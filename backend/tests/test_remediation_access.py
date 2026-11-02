import secrets
import uuid
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, override_settings
from django.utils import timezone
from PIL import Image

from apps.access.models import DeviceAccess, DeviceAdmission
from apps.catalog.gallery import ProductPhotosView
from apps.catalog.models import ProductPhoto
from apps.identity.models import Permission, RateBucket
from common.middleware import RequestBoundaryMiddleware
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf


def pending(token):
    client = Client(enforce_csrf_checks=True)
    response = post_with_csrf(client, "/api/v1/public/access/", {"public_token": token})
    assert response.status_code == 202, response.content
    return client, response.json()


def test_copied_link_is_pending_not_authorized_and_staff_must_approve(point_data, identity_data):
    browser, data = pending(point_data[1])
    assert DeviceAccess.objects.count() == 0
    assert set(data) == {"admission_id", "status", "expires_at", "verification_code"}
    assert settings.DEVICE_COOKIE_NAME not in browser.cookies
    assert browser.get("/api/v1/public/session/").status_code == 401
    assert browser.get("/api/v1/public/menu/").status_code == 401
    assert browser.get("/api/v1/staff/admissions/").status_code == 401
    assert (
        post_with_csrf(browser, "/api/v1/public/access/", {"public_token": point_data[1]}).json()
        == data
    )
    identifier = data["admission_id"]
    stranger = Client(enforce_csrf_checks=True)
    assert stranger.get(f"/api/v1/public/admissions/{identifier}/").status_code == 404
    assert (
        post_with_csrf(browser, f"/api/v1/public/admissions/{identifier}/claim/", {}).status_code
        == 404
    )
    staff = pin_client()
    command = {"idempotency_key": str(uuid.uuid4()), "status": "APPROVED"}
    path = f"/api/v1/staff/admissions/{identifier}/decision/"
    assert post_with_csrf(browser, path, command).status_code == 401
    assert staff.get(f"/api/v1/staff/admissions/?point={point_data[0].id}").json()["count"] == 1
    assert post_with_csrf(staff, path, command).status_code == 200
    assert post_with_csrf(staff, path, command).status_code == 200
    assert post_with_csrf(staff, path, {**command, "status": "REJECTED"}).status_code == 409
    assert (
        post_with_csrf(stranger, f"/api/v1/public/admissions/{identifier}/claim/", {}).status_code
        == 404
    )
    assert (
        post_with_csrf(browser, f"/api/v1/public/admissions/{identifier}/claim/", {}).status_code
        == 200
    )
    assert browser.get("/api/v1/public/context/").status_code == 200
    assert (
        post_with_csrf(
            browser, "/api/v1/public/access/", {"public_token": point_data[1]}
        ).status_code
        == 200
    )
    assert DeviceAccess.objects.count() == 1


def test_admission_rejection_expiry_and_cross_unit_are_enforced(point_data, identity_data):
    browser, data = pending(point_data[1])
    admission = DeviceAdmission.objects.get(id=data["admission_id"])
    foreign_staff = identity_data[3][0]
    with pytest.raises(IntegrityError), transaction.atomic():
        DeviceAdmission.objects.filter(id=admission.id).update(
            status="APPROVED", decided_by=foreign_staff
        )
    staff = pin_client()
    assert (
        post_with_csrf(
            staff,
            f"/api/v1/staff/admissions/{admission.id}/decision/",
            {
                "idempotency_key": str(uuid.uuid4()),
                "status": "REJECTED",
            },
        ).status_code
        == 200
    )
    assert browser.get(f"/api/v1/public/admissions/{admission.id}/").json()["status"] == "REJECTED"
    assert (
        post_with_csrf(
            browser, "/api/v1/public/access/", {"public_token": point_data[1]}
        ).status_code
        == 403
    )
    browser, data = pending(point_data[1])
    DeviceAdmission.objects.filter(id=data["admission_id"]).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert (
        browser.get(f"/api/v1/public/admissions/{data['admission_id']}/").json()["status"]
        == "EXPIRED"
    )
    assert (
        post_with_csrf(
            staff,
            f"/api/v1/staff/admissions/{data['admission_id']}/decision/",
            {
                "idempotency_key": str(uuid.uuid4()),
                "status": "APPROVED",
            },
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "generic,specific,expected",
    [(True, True, 200), (True, False, 403), (False, True, 403), (False, False, 403)],
)
def test_rotation_requires_both_grants_and_retries_are_idempotent(
    point_data, identity_data, generic, specific, expected
):
    admin = owner_client(identity_data)
    owner = identity_data[1]
    codes = ["MANAGE_SERVICE_POINTS", "ROTATE_SERVICE_POINT_TOKEN"]
    owner.permissions.remove(*Permission.objects.filter(code__in=codes))
    owner.permissions.add(
        *Permission.objects.filter(
            code__in=[c for c, enabled in zip(codes, [generic, specific], strict=True) if enabled]
        )
    )
    point = point_data[0]
    command = {
        "action": "ROTATE",
        "expected_version": 1,
        "confirmed": True,
        "reason": "synthetic",
        "idempotency_key": str(uuid.uuid4()),
    }
    path = f"/api/v1/admin/service-points/{point.id}/identifier/"
    assert post_with_csrf(admin, path, command).status_code == expected
    if expected == 200:
        assert post_with_csrf(admin, path, command).status_code == 200
        point.refresh_from_db()
        assert point.token_version == 2
        assert (
            post_with_csrf(
                admin, path, {**command, "idempotency_key": str(uuid.uuid4())}
            ).status_code
            == 409
        )
        assert post_with_csrf(admin, path, {**command, "reason": "changed"}).status_code == 409


def test_rotation_preserves_devices_normally_but_compromise_revokes(point_data, identity_data):
    browser = customer(point_data[1])
    waiting, pending_data = pending(point_data[1])
    admin = owner_client(identity_data)
    point = point_data[0]
    path = f"/api/v1/admin/service-points/{point.id}/identifier/"
    command = {"action": "ROTATE", "expected_version": 1, "confirmed": True, "reason": "normal"}
    assert post_with_csrf(admin, path, command).status_code == 200
    assert browser.get("/api/v1/public/context/").status_code == 200
    assert (
        waiting.get(f"/api/v1/public/admissions/{pending_data['admission_id']}/").json()["status"]
        == "REVOKED"
    )
    assert (
        post_with_csrf(
            Client(enforce_csrf_checks=True),
            "/api/v1/public/access/",
            {"public_token": point_data[1]},
        ).status_code
        == 404
    )
    assert (
        post_with_csrf(
            admin, path, {**command, "expected_version": 2, "revoke_devices": True}
        ).status_code
        == 200
    )
    assert browser.get("/api/v1/public/context/").status_code == 401


@pytest.mark.parametrize("index", [0, 1])
def test_staff_from_another_unit_or_company_cannot_decide_admission(point_data, identity_data, index):
    _, data = pending(point_data[1])
    foreign = identity_data[3][index]
    foreign.permissions.add(*Permission.objects.filter(code__in=["VIEW_OPERATION", "APPROVE_DEVICE_ACCESS"]))
    staff = Client(enforce_csrf_checks=True)
    assert post_with_csrf(staff, "/api/v1/staff/login/", {
        "company": foreign.unit.company.slug, "unit": foreign.unit.slug,
        "login_code": foreign.login_code, "pin": "123456",
    }).status_code == 200
    assert staff.get("/api/v1/staff/admissions/").json()["count"] == 0
    assert post_with_csrf(staff, f"/api/v1/staff/admissions/{data['admission_id']}/decision/", {
        "status": "APPROVED", "idempotency_key": str(uuid.uuid4()),
    }).status_code == 404


def test_manual_receipt_reconciliation_is_scoped_to_same_actor_and_unit(point_data, catalog_data, identity_data):
    from tests.test_orders import payload

    waiter = pin_client()
    command = {**payload(catalog_data), "point_id": str(point_data[0].id)}
    result = post_with_csrf(waiter, "/api/v1/staff/orders/", command)
    assert result.status_code == 201
    path = f"/api/v1/staff/manual-order-receipts/{command['idempotency_key']}/?point={point_data[0].id}"
    assert waiter.get(path).json() == result.json()
    assert post_with_csrf(waiter, "/api/v1/staff/orders/", command).json() == result.json()
    assert owner_client(identity_data).get(path).status_code == 404
    assert Client().get(path).status_code == 401


def test_abandoning_uncertain_manual_attempt_prevents_late_submission_without_deleting_orders(point_data, catalog_data):
    from apps.orders.models import OrderBatch
    from tests.test_orders import payload

    waiter = pin_client()
    command = {**payload(catalog_data), "point_id": str(point_data[0].id), "expected_session_id": None}
    path = f"/api/v1/staff/manual-order-receipts/{command['idempotency_key']}/"
    assert post_with_csrf(waiter, path, {"point": str(point_data[0].id)}).json() == {"abandoned": True}
    assert post_with_csrf(waiter, "/api/v1/staff/orders/", command).status_code == 409
    assert OrderBatch.objects.count() == 0
    confirmed = {**command, "idempotency_key": str(uuid.uuid4())}
    result = post_with_csrf(waiter, "/api/v1/staff/orders/", confirmed)
    assert result.status_code == 201
    existing = f"/api/v1/staff/manual-order-receipts/{confirmed['idempotency_key']}/"
    assert post_with_csrf(waiter, existing, {"point": str(point_data[0].id)}).json() == result.json()
    assert OrderBatch.objects.count() == 1
    stale = {**command, "idempotency_key": str(uuid.uuid4())}
    assert post_with_csrf(waiter, "/api/v1/staff/orders/", stale).status_code == 409


@pytest.mark.django_db
def test_bootstrap_has_no_anonymous_db_sessions_and_limits_work_under_nat(settings):
    settings.BOOTSTRAP_IP_LIMIT = 4
    settings.BOOTSTRAP_BROWSER_LIMIT = 2
    clients = [Client(enforce_csrf_checks=True) for _ in range(3)]
    for browser in clients:
        response = browser.get("/api/v1/csrf/")
        assert response.status_code == 200
        assert response.cookies[settings.BROWSER_COOKIE_NAME]["httponly"]
    assert Session.objects.count() == 0
    assert clients[0].get("/api/v1/csrf/").status_code == 200
    assert clients[1].get("/api/v1/csrf/").status_code == 429
    assert Session.objects.count() == 0
    RateBucket.objects.update(window=0)
    assert clients[1].get("/api/v1/csrf/").status_code == 200
    settings.HEALTH_IP_LIMIT = 1
    assert clients[0].get("/api/v1/health/").status_code == 200
    assert clients[1].get("/api/v1/health/").status_code == 429


def noisy_image():
    output = BytesIO()
    Image.frombytes("RGB", (256, 256), secrets.token_bytes(256 * 256 * 3)).save(output, "PNG")
    assert 65536 < len(output.getvalue()) < 2 * 1024 * 1024
    return SimpleUploadedFile("synthetic.png", output.getvalue(), content_type="image/png")


def test_gallery_accepts_large_valid_multipart_without_relaxing_other_routes(
    identity_data, catalog_data
):
    admin = owner_client(identity_data)
    path = f"/api/v1/admin/products/{catalog_data[3].id}/photos/"
    media = Path(__file__).resolve().parents[2] / ".local" / ("gallery-v2-" + uuid.uuid4().hex)
    media.mkdir()
    with override_settings(MEDIA_ROOT=media):
        token = admin.get("/api/v1/csrf/").json()["csrf_token"]
        response = admin.post(
            path,
            {"idempotency_key": str(uuid.uuid4()), "image": noisy_image()},
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201, response.content
        assert ProductPhoto.objects.count() == 1
        assert Client().post(path, {"image": noisy_image()}).status_code in {401, 403}
        assert (
            admin.post(
                path, b"broken", content_type="multipart/form-data", HTTP_X_CSRFTOKEN=token
            ).status_code
            == 400
        )
        assert (
            admin.post(
                path,
                {
                    "idempotency_key": str(uuid.uuid4()),
                    "image": SimpleUploadedFile("bad.png", b"bad"),
                },
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 400
        )
        oversized = SimpleUploadedFile("big.png", b"x" * (settings.PRODUCT_IMAGE_MAX_BYTES + 65537))
        assert (
            admin.post(
                path,
                {"idempotency_key": str(uuid.uuid4()), "image": oversized},
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 413
        )
        request = RequestFactory().post(
            path,
            {"idempotency_key": str(uuid.uuid4()), "image": noisy_image()},
            HTTP_X_CSRFTOKEN=token,
        )
        request.COOKIES = {name: item.value for name, item in admin.cookies.items()}
        request.session = admin.session
        request.user = get_user(request)
        del request.META["CONTENT_LENGTH"]
        response = RequestBoundaryMiddleware(
            lambda req: ProductPhotosView.as_view()(req, identifier=catalog_data[3].id)
        )(request)
        assert response.status_code == 201, getattr(response, "data", None)
        assert ProductPhoto.objects.count() == 2

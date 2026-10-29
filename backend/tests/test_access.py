import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.conf import settings
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, RequestFactory
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.access.models import DeviceAccess, ServicePoint
from apps.access.services import cipher, digest, exchange, point_url
from tests.test_identity import owner_client, post_with_csrf


def customer(token):
    client = Client(enforce_csrf_checks=True)
    result = post_with_csrf(client, "/api/v1/public/access/", {"public_token": token})
    assert result.status_code == 200, result.content
    return client


def test_access_is_bound_idempotent_and_has_no_staff_privilege(point_data):
    point, token = point_data
    client = Client(enforce_csrf_checks=True)
    assert client.get("/api/v1/public/context/").status_code == 401
    assert (
        client.post(
            "/api/v1/public/access/", {"public_token": token}, content_type="application/json"
        ).status_code
        == 403
    )
    for _ in range(2):
        result = post_with_csrf(client, "/api/v1/public/access/", {"public_token": token})
        assert result.status_code == 200
        assert result.json()["point"]["name"] == "Mesa 07"
        assert token.encode() not in result.content and b"token_digest" not in result.content
        assert result.cookies[settings.DEVICE_COOKIE_NAME]["httponly"]
    assert DeviceAccess.objects.filter(point=point).count() == 1
    client.cookies.pop(settings.DEVICE_COOKIE_NAME)
    assert (
        post_with_csrf(client, "/api/v1/public/access/", {"public_token": token}).status_code == 200
    )
    assert DeviceAccess.objects.count() == 1
    assert client.get("/api/v1/staff/me/").status_code == 401
    assert client.get("/api/v1/admin/staff/").status_code == 401


def test_copied_static_url_creates_new_browser_access_without_proving_presence(point_data):
    _, token = point_data
    first, second = customer(token), customer(token)
    assert (
        first.cookies[settings.DEVICE_COOKIE_NAME].value
        != second.cookies[settings.DEVICE_COOKIE_NAME].value
    )
    assert DeviceAccess.objects.count() == 2


def test_expiry_revocation_and_point_status_are_checked_each_request(point_data, identity_data):
    point, token = point_data
    client = customer(token)
    device = DeviceAccess.objects.get(point=point)
    admin = owner_client(identity_data)
    assert (
        post_with_csrf(
            admin, f"/api/v1/admin/device-access/{device.id}/revoke/", {"reason": "Revogação"}
        ).status_code
        == 204
    )
    assert client.get("/api/v1/public/context/").status_code == 401
    client = customer(token)
    device = DeviceAccess.objects.filter(revoked_at__isnull=True).get()
    # Move both timestamps to preserve the database's positive TTL invariant.
    DeviceAccess.objects.filter(id=device.id).update(
        issued_at=timezone.now() - timedelta(hours=13),
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert client.get("/api/v1/public/context/").status_code == 401
    point.active = False
    point.save()
    assert (
        post_with_csrf(client, "/api/v1/public/access/", {"public_token": token}).status_code == 404
    )


def test_point_admin_is_scoped_and_creation_is_idempotent(identity_data):
    admin = owner_client(identity_data)
    payload = {
        "name": "Mesa 01",
        "number": 1,
        "type": "TABLE",
        "idempotency_key": str(uuid.uuid4()),
    }
    first = post_with_csrf(admin, "/api/v1/admin/service-points/", payload)
    assert first.status_code == 201
    second = post_with_csrf(admin, "/api/v1/admin/service-points/", payload)
    assert first.json() == second.json() and ServicePoint.objects.count() == 1
    assert (
        post_with_csrf(
            admin, "/api/v1/admin/service-points/", {**payload, "name": "Changed"}
        ).status_code
        == 409
    )
    assert (
        post_with_csrf(
            admin,
            "/api/v1/admin/service-points/",
            {**payload, "unit_id": str(identity_data[3][0].unit_id)},
        ).status_code
        == 400
    )
    point = ServicePoint.objects.get()
    url = admin.get(f"/api/v1/admin/service-points/{point.id}/url/").json()["url"]
    assert url == point_url(point) and url.endswith(
        cipher().decrypt(bytes(point.token_ciphertext)).decode()
    )
    qr = admin.get(f"/api/v1/admin/service-points/{point.id}/qr/")
    assert qr.status_code == 200 and qr["Content-Type"] == "image/svg+xml"
    assert b"<svg" in qr.content and b"<path" in qr.content
    assert "attachment;" in qr["Content-Disposition"]
    with pytest.raises(IntegrityError), transaction.atomic():
        ServicePoint.objects.filter(id=point.id).update(unit=identity_data[3][0].unit)
    foreign_token = secrets.token_urlsafe(32)
    foreign = ServicePoint.objects.create(
        unit=identity_data[3][0].unit,
        name="Foreign",
        type="TABLE",
        number=1,
        token_digest=digest(foreign_token),
        token_ciphertext=cipher().encrypt(foreign_token.encode()),
    )
    assert admin.get(f"/api/v1/admin/service-points/{foreign.id}/url/").status_code == 404
    assert admin.get(f"/api/v1/admin/service-points/{foreign.id}/devices/").status_code == 404


@pytest.mark.django_db(transaction=True)
def test_five_device_limit_is_atomic_under_ten_browsers(identity_data, point_data):
    point, token = point_data
    barrier = Barrier(10)

    def attempt(_):
        close_old_connections()
        request = RequestFactory().post("/api/v1/public/access/")
        request.session = {"tapserve_browser_nonce": secrets.token_urlsafe(32)}
        barrier.wait(timeout=10)
        try:
            exchange(request, token)
            return 200
        except APIException as error:
            return error.status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(10)))
    assert results.count(200) == 5 and results.count(409) == 5
    assert DeviceAccess.objects.filter(point=point, revoked_at__isnull=True).count() == 5

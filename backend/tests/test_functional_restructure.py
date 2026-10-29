import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.access.models import DeviceAccess, ServicePoint
from apps.access.services import cipher, digest
from apps.catalog.models import Option, OptionGroup, Product
from apps.catalog.video import validate_video
from apps.identity.authentication import StaffIdentity
from apps.identity.models import AuditEvent, Role, Staff
from apps.identity.serializers import StaffInput
from apps.identity.services import create_staff
from apps.orders.models import (
    OrderBatch,
    OrderItem,
    ProductionAssignment,
    RealtimeLease,
    SelectedOption,
)
from tests.media import mp4_metadata, webm_metadata
from tests.test_access import customer
from tests.test_client_experience_update import patch
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_interventions import command
from tests.test_orders import payload
from tests.test_production import mutate


def test_customer_manual_orders_feed_scope_kds_totals_and_counts(
    identity_data, point_data, catalog_data
):
    admin, waiter = owner_client(identity_data), pin_client()
    own = customer(point_data[1])
    created = post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data))
    assert created.status_code == 201
    batch_id = created.json()["batch"]["id"]
    assert admin.get("/api/v1/staff/orders/?status=NEW").json()["results"][0]["id"] == batch_id
    assert waiter.get("/api/v1/staff/orders/").json()["results"][0]["origin"] == "CUSTOMER"
    manual = {**payload(catalog_data), "point_id": str(point_data[0].id)}
    result = post_with_csrf(waiter, "/api/v1/staff/orders/", manual)
    assert result.status_code == 201
    assert post_with_csrf(waiter, "/api/v1/staff/orders/", manual).json() == result.json()
    assert OrderBatch.objects.count() == 2
    table = waiter.get("/api/v1/staff/tables/").json()["results"][0]
    assert (table["order_count"], table["active_order_count"], table["subtotal"]) == (2, 2, "49.40")
    assert {batch["id"] for batch in own.get("/api/v1/public/orders/").json()["results"]} == {
        str(batch.id) for batch in OrderBatch.objects.all()
    }
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    assert admin.get("/api/v1/staff/production/items/").json()["count"] == 2
    item = OrderItem.objects.get(batch_id=result.json()["batch"]["id"])
    cancelled = post_with_csrf(admin, f"/api/v1/staff/items/{item.id}/cancel/", command(item))
    assert cancelled.status_code == 200
    table = waiter.get("/api/v1/staff/tables/").json()["results"][0]
    assert (table["order_count"], table["active_order_count"], table["subtotal"]) == (2, 1, "24.70")
    foreign = ServicePoint.objects.create(
        unit=identity_data[3][0].unit,
        name="Foreign",
        type="TABLE",
        number=7,
        token_digest=digest("foreign"),
        token_ciphertext=cipher().encrypt(b"foreign"),
    )
    assert (
        post_with_csrf(
            waiter,
            "/api/v1/staff/orders/",
            {**manual, "point_id": str(foreign.id), "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 404
    )
    assert all(
        row["id"] != str(foreign.id)
        for row in waiter.get("/api/v1/staff/tables/").json()["results"]
    )


def test_manual_starts_session_without_device_and_can_edit_until_production(
    identity_data, point_data, catalog_data
):
    admin = owner_client(identity_data)
    body = {**payload(catalog_data), "point_id": str(point_data[0].id)}
    body["items"][0]["participant_name"] = ""
    response = post_with_csrf(admin, "/api/v1/staff/orders/", body)
    assert response.status_code == 201 and not DeviceAccess.objects.exists()
    item = OrderItem.objects.get()
    data = {
        **command(item),
        "quantity": 3,
        "option_ids": [str(catalog_data[-1].id)],
        "notes": "Sem sal",
        "participant_id": None,
    }
    assert patch(admin, f"/api/v1/staff/items/{item.id}/", data).status_code == 200
    item.refresh_from_db()
    assert item.line_total == Decimal("37.05") and item.notes == "Sem sal"
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    assert mutate(admin, item, "NEW", "ACCEPTED").status_code == 200
    assert mutate(admin, item, "ACCEPTED", "PREPARING").status_code == 200
    assert (
        patch(
            admin,
            f"/api/v1/staff/items/{item.id}/",
            {**data, "idempotency_key": str(uuid.uuid4()), "expected_version": item.version},
        ).status_code
        == 409
    )


def test_cleaning_check_cutlery_filters_claim_resolution_and_history(
    identity_data, point_data, catalog_data
):
    own, waiter = customer(point_data[1]), pin_client()
    for kind in ["CLEANING", "CUTLERY"]:
        body = {"kind": kind, "idempotency_key": str(uuid.uuid4())}
        result = post_with_csrf(own, "/api/v1/public/service-requests/", body)
        assert result.status_code == 201
        assert post_with_csrf(own, "/api/v1/public/service-requests/", body).json() == result.json()
        if kind == "CLEANING":
            assert (
                post_with_csrf(
                    own,
                    "/api/v1/public/service-requests/",
                    {**body, "idempotency_key": str(uuid.uuid4())},
                ).status_code
                == 409
            )
        assert waiter.get(f"/api/v1/staff/tables/?filter={kind}").json()["count"] == 1
        call = result.json()
        for old, new in [("OPEN", "ASSIGNED"), ("ASSIGNED", "RESOLVED")]:
            response = post_with_csrf(
                waiter,
                f"/api/v1/staff/service-requests/{call['id']}/status/",
                {"expected_status": old, "status": new, "idempotency_key": str(uuid.uuid4())},
            )
            assert response.status_code == 200
        assert waiter.get(f"/api/v1/staff/tables/?filter={kind}").json()["count"] == 0
    assert waiter.get("/api/v1/staff/service-requests/?status=RESOLVED").json()["count"] == 2
    assert waiter.get("/api/v1/staff/tables/").json()["results"][0]["pending_calls"] == []
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    own = customer(point_data[1])
    assert (
        post_with_csrf(
            own,
            "/api/v1/public/service-requests/",
            {"kind": "CHECK", "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 201
    )
    assert waiter.get("/api/v1/staff/tables/?filter=CHECK").json()["count"] == 1


def test_reusable_groups_direct_options_quote_snapshots_and_scope(
    identity_data, point_data, catalog_data
):
    admin, own = owner_client(identity_data), customer(point_data[1])
    menu, category, sector, first, group, option = catalog_data
    second = Product.objects.create(
        unit=identity_data[0],
        category=category,
        production_sector=sector,
        name="Segundo",
        base_price="20.00",
    )
    endpoint = f"/api/v1/admin/products/{second.id}/"
    assert (
        patch(
            admin,
            endpoint,
            {"option_group_ids": [str(group.id)], "individual_option_ids": [str(option.id)]},
        ).status_code
        == 200
    )
    assert group.products.count() == 2
    detail = own.get(f"/api/v1/public/products/{second.id}/").json()
    assert len(detail["groups"]) == 1 and detail["individual_options"] == []
    assert patch(admin, endpoint, {"option_group_ids": []}).status_code == 200
    detail = own.get(f"/api/v1/public/products/{second.id}/").json()
    assert detail["groups"] == [] and detail["individual_options"][0]["id"] == str(option.id)
    body = payload(catalog_data)
    body["items"][0]["product_id"] = str(second.id)
    result = post_with_csrf(own, "/api/v1/public/orders/", body)
    assert result.status_code == 201
    item = OrderItem.objects.get()
    assert (
        item.unit_price == Decimal("22.25")
        and SelectedOption.objects.get(item=item).group_name == "Adicionais"
    )
    Option.objects.filter(id=option.id).update(additional_price="99.00")
    item.refresh_from_db()
    assert (
        item.unit_price == Decimal("22.25")
        and item.snapshot["options"][0]["additional_price"] == "2.25"
    )
    foreign_product = Product.objects.create(
        unit=identity_data[3][0].unit,
        name="Foreign",
        category=type(category).objects.create(
            menu=type(menu).objects.create(unit=identity_data[3][0].unit, name="Other"),
            name="Other",
        ),
        production_sector=type(sector).objects.create(unit=identity_data[3][0].unit, name="Other"),
        base_price="1.00",
    )
    foreign_group = OptionGroup.objects.create(
        product=foreign_product, name="Foreign", selection_type="SINGLE"
    )
    assert patch(admin, endpoint, {"option_group_ids": [str(foreign_group.id)]}).status_code == 400
    with pytest.raises(IntegrityError), transaction.atomic():
        second.applied_option_groups.add(foreign_group)


def test_point_number_name_optional_reason_preserves_token_and_session(
    identity_data, point_data, catalog_data
):
    admin, own = owner_client(identity_data), customer(point_data[1])
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    point = point_data[0]
    original = (point.token_digest, point.token_version, OrderBatch.objects.get().session_id)
    assert (
        patch(
            admin, f"/api/v1/admin/service-points/{point.id}/", {"number": 8, "name": ""}
        ).status_code
        == 200
    )
    point.refresh_from_db()
    assert (
        point.token_digest,
        point.token_version,
        OrderBatch.objects.get().session_id,
    ) == original
    assert own.get("/api/v1/public/context/").json()["point"]["number"] == 8
    assert own.get("/api/v1/public/session/").json()["point"]["number"] == 8
    for number in [None, 0, -1, 1.5, "abc"]:
        assert (
            post_with_csrf(
                admin,
                "/api/v1/admin/service-points/",
                {"type": "TABLE", "number": number, "idempotency_key": str(uuid.uuid4())},
            ).status_code
            == 400
        )
    assert (
        post_with_csrf(
            admin,
            "/api/v1/admin/service-points/",
            {"type": "TABLE", "number": 8, "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 400
    )
    assert AuditEvent.objects.get(action="POINT_UPDATED").reason == ""


def test_staff_idempotency_same_name_soft_delete_and_revocation(identity_data):
    admin, waiter = owner_client(identity_data), pin_client()
    body = {
        "name": "Mesmo nome",
        "login_code": "first",
        "pin": "234567",
        "role_id": str(Role.objects.get(unit=identity_data[0], name="WAITER").id),
        "permissions": ["VIEW_OPERATION"],
        "idempotency_key": str(uuid.uuid4()),
    }
    first = post_with_csrf(admin, "/api/v1/admin/staff/", body)
    assert first.status_code == 201
    assert post_with_csrf(admin, "/api/v1/admin/staff/", body).json() == first.json()
    assert Staff.objects.filter(login_code="first").count() == 1
    assert (
        post_with_csrf(
            admin,
            "/api/v1/admin/staff/",
            {**body, "login_code": "second", "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 201
    )
    target = identity_data[2]
    endpoint = f"/api/v1/admin/staff/{target.id}/"
    assert patch(admin, endpoint, {"active": False}).status_code == 200
    assert waiter.get("/api/v1/staff/me/").status_code == 401
    assert patch(admin, endpoint, {"active": True}).status_code == 200
    reactivated = pin_client()
    assert reactivated.get("/api/v1/staff/me/").status_code == 200
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    response = admin.delete(endpoint, {}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 204
    target.refresh_from_db()
    assert not target.active and target.deleted_at
    assert reactivated.get("/api/v1/staff/me/").status_code == 401
    assert str(target.id) not in {
        row["id"] for row in admin.get("/api/v1/admin/staff/").json()["results"]
    }
    assert patch(admin, endpoint, {"active": True}).status_code == 404
    assert AuditEvent.objects.filter(
        action="STAFF_DELETED", resource_id=str(target.id), reason=""
    ).exists()
    assert (
        admin.delete(
            f"/api/v1/admin/staff/{identity_data[1].id}/",
            {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 403
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_staff_retries_create_one_identity(identity_data):
    actor = identity_data[1]
    barrier = Barrier(2)
    data = StaffInput(
        data={
            "name": "Concurrent",
            "login_code": "concurrent",
            "pin": "234567",
            "role_id": str(identity_data[2].role_id),
            "permissions": [],
            "idempotency_key": str(uuid.uuid4()),
        }
    )
    data.is_valid(raise_exception=True)

    def create(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return create_staff(
                StaffIdentity(
                    actor, True, frozenset(actor.permissions.values_list("code", flat=True))
                ),
                data.validated_data,
            ).id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(create, range(2)))
    assert ids[0] == ids[1] and Staff.objects.filter(login_code="concurrent").count() == 1


def test_presence_counts_live_acknowledged_devices_and_expires(identity_data, point_data):
    own = customer(point_data[1])
    waiter = pin_client()
    device = DeviceAccess.objects.get()
    DeviceAccess.objects.filter(id=device.id).update(last_seen_at=timezone.now())
    lease = RealtimeLease.objects.create(
        unit=identity_data[0],
        actor="D:" + str(device.id),
        acknowledged=True,
        expires_at=timezone.now() + timedelta(seconds=30),
    )
    assert waiter.get("/api/v1/staff/tables/").json()["results"][0]["connected_devices"] == 1
    RealtimeLease.objects.filter(id=lease.id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert waiter.get("/api/v1/staff/tables/").json()["results"][0]["connected_devices"] == 0
    assert own.get("/api/v1/public/context/").status_code == 200


def test_table_summary_queries_do_not_grow_per_table(identity_data, point_data, catalog_data):
    own, waiter = customer(point_data[1]), pin_client()
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    with CaptureQueriesContext(connection) as small:
        response = waiter.get("/api/v1/staff/tables/")
    assert response.status_code == 200
    for number in range(10, 20):
        token = uuid.uuid4().hex
        ServicePoint.objects.create(
            unit=identity_data[0],
            number=number,
            type="TABLE",
            token_digest=digest(token),
            token_ciphertext=cipher().encrypt(token.encode()),
        )
    with CaptureQueriesContext(connection) as large:
        response = waiter.get("/api/v1/staff/tables/")
    assert response.json()["count"] == 11
    assert len(small) == len(large) and len(large) <= 20


@pytest.mark.parametrize(
    "name,raw,extension",
    [
        ("a.mp4", mp4_metadata(), "mp4"),
        ("a.mov", mp4_metadata(brand=b"qt  "), "mp4"),
        ("a.webm", webm_metadata(), "webm"),
    ],
)
def test_video_without_binary_validates_container_and_codecs(
    name, raw, extension, settings, monkeypatch
):
    settings.FFPROBE_BINARY = ""
    monkeypatch.setattr("apps.catalog.video.shutil.which", lambda _: None)
    file = SimpleUploadedFile(name, raw)
    assert validate_video(file) == extension and file.tell() == 0


@pytest.mark.parametrize(
    "raw",
    [
        b"<script>alert(1)</script>",
        mp4_metadata(codec=b"hvc1"),
        mp4_metadata()[:-3],
        webm_metadata(codec=b"UNSUPPORTED"),
        b"\x1a\x45\xdf\xa3\x00",
    ],
)
def test_video_rejects_invalid_incompatible_and_truncated_files(raw, monkeypatch):
    monkeypatch.setattr("apps.catalog.video.shutil.which", lambda _: None)
    with pytest.raises(ValidationError):
        validate_video(SimpleUploadedFile("a.mp4", raw))


def test_video_accepts_large_bounded_content_and_rejects_mismatched_extension(
    settings, monkeypatch
):
    monkeypatch.setattr("apps.catalog.video.shutil.which", lambda _: None)
    raw = mp4_metadata(payload=b"\x65" + b"\x88" * (2 * 1024 * 1024))
    settings.PRODUCT_VIDEO_MAX_BYTES = len(raw)
    assert validate_video(SimpleUploadedFile("large.mp4", raw)) == "mp4"
    with pytest.raises(ValidationError):
        validate_video(SimpleUploadedFile("wrong.webm", raw))
    settings.PRODUCT_VIDEO_MAX_BYTES = len(raw) - 1
    with pytest.raises(ValidationError):
        validate_video(SimpleUploadedFile("large.mp4", raw))

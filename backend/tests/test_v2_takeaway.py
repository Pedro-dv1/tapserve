import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.utils.module_loading import import_string

from apps.access.models import DeviceAccess
from apps.catalog.models import Product
from apps.orders.models import OrderBatch, OrderItem, ServiceRequest, ServiceSession
from apps.orders.serializers import OrderInput
from apps.orders.services import submit_order
from apps.organizations.models import Unit
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload
from tests.test_production import mutate


def enable(unit, **settings):
    Unit.objects.filter(id=unit.id).update(**settings)
    unit.refresh_from_db()


def test_mixed_order_preserves_modes_authoritative_price_pipeline_and_subtotal(
    identity_data, point_data, catalog_data
):
    enable(identity_data[0], table_takeaway_enabled=True)
    device = customer(point_data[1])
    body = payload(catalog_data)
    line = body["items"][0]
    body["items"] = [line, {**line, "fulfillment_mode": "TAKEAWAY", "expected_unit_price": "12.35"}]
    result = post_with_csrf(device, "/api/v1/public/orders/", body)
    assert result.status_code == 201, result.content
    receipt = result.json()
    assert receipt["batch"]["channel"] == "TABLE"
    assert {item["fulfillment_mode"] for item in receipt["batch"]["items"]} == {
        "DINE_IN",
        "TAKEAWAY",
    }
    assert OrderBatch.objects.count() == ServiceSession.objects.count() == 1
    assert OrderItem.objects.count() == 2
    assert post_with_csrf(device, "/api/v1/public/orders/", body).json() == receipt
    admin = owner_client(identity_data)
    waiter = pin_client()
    for client in (admin, waiter):
        batches = client.get("/api/v1/staff/orders/").json()["results"]
        assert {item["fulfillment_mode"] for item in batches[0]["items"]} == {"DINE_IN", "TAKEAWAY"}
        assert client.get("/api/v1/staff/tables/").json()["results"][0]["subtotal"] == "49.40"
    assert admin.get("/api/v1/staff/production/items/").json()["count"] == 2
    item = OrderItem.objects.get(fulfillment_mode="TAKEAWAY")
    assert item.snapshot["fulfillment_mode"] == "TAKEAWAY"
    for before, after in [("NEW", "ACCEPTED"), ("ACCEPTED", "PREPARING"), ("PREPARING", "READY")]:
        assert mutate(admin, item, before, after).status_code == 200
    assert mutate(waiter, item, "READY", "DELIVERING").status_code == 200
    assert mutate(waiter, item, "DELIVERING", "DELIVERED").status_code == 200
    cancelled = post_with_csrf(
        admin,
        f"/api/v1/staff/items/{item.id}/cancel/",
        {
            "idempotency_key": str(uuid.uuid4()),
            "expected_version": 6,
        },
    )
    assert cancelled.status_code == 409
    item.refresh_from_db()
    assert item.fulfillment_mode == "TAKEAWAY" and item.status == "DELIVERED"


def test_flags_product_eligibility_and_price_change_fail_without_partial_orders(
    identity_data, point_data, catalog_data
):
    device = customer(point_data[1])
    body = payload(catalog_data)
    body["items"][0]["fulfillment_mode"] = "TAKEAWAY"
    response = post_with_csrf(device, "/api/v1/public/orders/", body)
    assert response.status_code == 400 and response.json()["error"]["code"] == "TAKEAWAY_DISABLED"
    enable(identity_data[0], table_takeaway_enabled=True)
    Product.objects.filter(id=catalog_data[3].id).update(takeaway_allowed=False)
    response = post_with_csrf(device, "/api/v1/public/orders/", body)
    assert (
        response.status_code == 400 and response.json()["error"]["code"] == "TAKEAWAY_NOT_ALLOWED"
    )
    Product.objects.filter(id=catalog_data[3].id).update(takeaway_allowed=True)
    body["items"][0]["expected_unit_price"] = "0.01"
    response = post_with_csrf(device, "/api/v1/public/orders/", body)
    assert response.status_code == 409 and response.json()["error"]["code"] == "PRICE_CHANGED"
    assert OrderBatch.objects.count() == ServiceSession.objects.count() == 0
    body["items"][0]["expected_unit_price"] = "12.35"
    assert post_with_csrf(device, "/api/v1/public/orders/", body).status_code == 201


def test_manual_channel_edit_mode_and_disable_keeps_existing_takeaway(
    identity_data, point_data, catalog_data
):
    enable(identity_data[0], table_takeaway_enabled=True)
    admin = owner_client(identity_data)
    body = {**payload(catalog_data), "point_id": str(point_data[0].id)}
    assert (
        post_with_csrf(admin, "/api/v1/staff/orders/", body).json()["batch"]["channel"] == "STAFF"
    )
    item = OrderItem.objects.get()
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]

    def edit(mode, version):
        return admin.patch(
            f"/api/v1/staff/items/{item.id}/",
            {
                "idempotency_key": str(uuid.uuid4()),
                "expected_version": version,
                "quantity": 3,
                "option_ids": [str(catalog_data[5].id)],
                "notes": "Embalar",
                "fulfillment_mode": mode,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    assert edit("TAKEAWAY", 1).status_code == 200
    enable(identity_data[0], table_takeaway_enabled=False)
    assert edit("TAKEAWAY", 2).status_code == 200
    item.refresh_from_db()
    assert item.snapshot["fulfillment_mode"] == item.fulfillment_mode == "TAKEAWAY"
    assert item.line_total == Decimal("37.05")


def test_packaging_is_a_scoped_deduplicated_service_request_without_food_charge(
    identity_data, point_data, catalog_data
):
    device = customer(point_data[1])
    body = {"idempotency_key": str(uuid.uuid4()), "kind": "PACKAGING"}
    assert post_with_csrf(device, "/api/v1/public/service-requests/", body).status_code == 400
    enable(identity_data[0], leftover_packaging_enabled=True)
    assert post_with_csrf(device, "/api/v1/public/service-requests/", body).status_code == 400
    assert (
        post_with_csrf(device, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    call = post_with_csrf(device, "/api/v1/public/service-requests/", body)
    assert call.status_code == 201, call.content
    assert post_with_csrf(device, "/api/v1/public/service-requests/", body).json() == call.json()
    # Create directly under the existing service lock to exercise deduplication, not its rate limiter.
    from apps.orders.service_requests import RequestInput, _create_request
    from common.idempotency import Conflict

    data = RequestInput(data={**body, "idempotency_key": str(uuid.uuid4())})
    data.is_valid(raise_exception=True)
    with pytest.raises(Conflict):
        _create_request(DeviceAccess.objects.get(), data.validated_data)
    waiter = pin_client()
    identifier = call.json()["id"]
    assert waiter.get("/api/v1/staff/tables/?filter=PACKAGING").json()["count"] == 1
    for before, target in [("OPEN", "ASSIGNED"), ("ASSIGNED", "RESOLVED")]:
        assert (
            post_with_csrf(
                waiter,
                f"/api/v1/staff/service-requests/{identifier}/status/",
                {
                    "idempotency_key": str(uuid.uuid4()),
                    "expected_status": before,
                    "status": target,
                },
            ).status_code
            == 200
        )
    assert (
        OrderBatch.objects.count()
        == OrderItem.objects.count()
        == ServiceRequest.objects.count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_mixed_order_retry_creates_one_batch(identity_data, point_data, catalog_data):
    enable(identity_data[0], table_takeaway_enabled=True)
    device_client = customer(point_data[1])
    device = DeviceAccess.objects.get()
    device.point.unit.refresh_from_db()
    body = payload(catalog_data)
    body["items"].append({**body["items"][0], "fulfillment_mode": "TAKEAWAY"})
    data = OrderInput(data=body)
    data.is_valid(raise_exception=True)
    barrier = Barrier(2)

    def submit(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return submit_order(device, data.validated_data)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert json.loads(json.dumps(results[0], default=str)) == json.loads(
        json.dumps(results[1], default=str)
    )
    assert OrderBatch.objects.count() == ServiceSession.objects.count() == 1
    assert OrderItem.objects.count() == 2
    ServiceSession.objects.update(status="CLOSED")
    assert (
        post_with_csrf(device_client, "/api/v1/public/orders/", payload(catalog_data)).status_code
        == 401
    )
    assert OrderBatch.objects.count() == 1


def test_legacy_contract_and_channel_backfill(identity_data, point_data, catalog_data):
    data = OrderInput(data=payload(catalog_data))
    data.is_valid(raise_exception=True)
    assert "fulfillment_mode" not in data.validated_data["items"][0]
    admin = owner_client(identity_data)
    response = post_with_csrf(
        admin, "/api/v1/staff/orders/", {**payload(catalog_data), "point_id": str(point_data[0].id)}
    )
    assert response.status_code == 201
    item = OrderItem.objects.get()
    assert item.fulfillment_mode == "DINE_IN"
    OrderBatch.objects.update(channel="TABLE")
    from django.apps import apps
    from django.db import connection

    backfill = import_string(
        "apps.orders.migrations.0014_remove_servicerequest_request_kind_valid_and_more.backfill_channels"
    )
    with connection.schema_editor() as editor:
        backfill(apps, editor)
    assert OrderBatch.objects.get().channel == "STAFF"


def test_customer_mode_change_requires_attendant_after_acceptance(
    identity_data, point_data, catalog_data
):
    enable(identity_data[0], table_takeaway_enabled=True)
    device = customer(point_data[1])
    assert (
        post_with_csrf(device, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    item = OrderItem.objects.get()
    admin = owner_client(identity_data)
    assert mutate(admin, item, "NEW", "ACCEPTED").status_code == 200
    token = device.get("/api/v1/csrf/").json()["csrf_token"]
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "expected_version": 2,
        "quantity": 2,
        "option_ids": [str(catalog_data[5].id)],
        "notes": "",
        "fulfillment_mode": "TAKEAWAY",
    }
    assert (
        device.patch(
            f"/api/v1/public/items/{item.id}/",
            body,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 409
    )
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    assert (
        admin.patch(
            f"/api/v1/staff/items/{item.id}/",
            body,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )
    item.refresh_from_db()
    assert item.fulfillment_mode == "TAKEAWAY"

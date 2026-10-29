import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, connection, transaction

from apps.access.models import DeviceAccess
from apps.catalog.models import Product
from apps.identity.models import AuditEvent
from apps.orders.models import (
    OrderBatch,
    OrderItem,
    ServiceSession,
    SessionParticipant,
    SessionPoint,
)
from apps.orders.serializers import OrderInput
from apps.orders.services import submit_order
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf


def payload(catalog_data, key=None):
    return {
        "idempotency_key": str(key or uuid.uuid4()),
        "items": [
            {
                "product_id": str(catalog_data[3].id),
                "quantity": 2,
                "option_ids": [str(catalog_data[5].id)],
                "participant_name": "Pedro",
                "notes": "Sem pimenta",
            }
        ],
    }


def test_first_order_opens_one_occupation_and_associates_pending_devices(
    point_data, catalog_data, identity_data
):
    first, second = customer(point_data[1]), customer(point_data[1])
    assert ServiceSession.objects.count() == 0
    context = first.get("/api/v1/public/session/").json()
    assert context["session"] is None and context["point_status"] == "FREE"
    assert context["point"]["id"] == str(point_data[0].id)
    body = payload(catalog_data)
    response = post_with_csrf(first, "/api/v1/public/orders/", body)
    assert response.status_code == 201, response.content
    assert (
        ServiceSession.objects.count()
        == SessionPoint.objects.filter(ended_at__isnull=True).count()
        == 1
    )
    session = ServiceSession.objects.get()
    assert DeviceAccess.objects.filter(session=session).count() == 2
    assert second.get("/api/v1/public/session/").json()["session"]["id"] == str(session.id)
    assert second.get("/api/v1/public/orders/").json()["count"] == 1
    assert OrderItem.objects.get().line_total == Decimal("24.70")
    assert SessionParticipant.objects.get().display_name == "Pedro"
    admin = owner_client(identity_data)
    assert admin.get("/api/v1/staff/operation/").json()["count"] == 1
    assert (
        admin.get(f"/api/v1/staff/sessions/{session.id}/orders/").json()["results"][0]["id"]
        == response.json()["batch"]["id"]
    )
    assert post_with_csrf(first, "/api/v1/public/orders/", body).json() == response.json()
    assert (
        first.get(f"/api/v1/public/order-receipts/{body['idempotency_key']}/").json()
        == response.json()
    )
    assert (
        second.get(f"/api/v1/public/order-receipts/{body['idempotency_key']}/").status_code == 404
    )
    altered = {**body, "items": [{**body["items"][0], "quantity": 3}]}
    assert post_with_csrf(first, "/api/v1/public/orders/", altered).status_code == 409
    assert (
        OrderBatch.objects.count() == 1
        and AuditEvent.objects.filter(action="ORDER_CREATED").count() == 1
    )
    # Historic prices and names survive catalog changes.
    Product.objects.filter(id=catalog_data[3].id).update(
        name="Changed", base_price=Decimal("99.00")
    )
    item = first.get("/api/v1/public/orders/").json()["results"][0]["items"][0]
    assert item["snapshot"]["name"] == "Lanche" and item["line_total"] == "24.70"


def test_invalid_order_rolls_back_session_participants_and_items(point_data, catalog_data):
    client = customer(point_data[1])
    body = payload(catalog_data)
    bad = {
        **body,
        "items": [
            body["items"][0],
            {**body["items"][0], "option_ids": [], "participant_name": "João"},
        ],
    }
    assert post_with_csrf(client, "/api/v1/public/orders/", bad).status_code == 400
    assert (
        ServiceSession.objects.count()
        == OrderBatch.objects.count()
        == OrderItem.objects.count()
        == SessionParticipant.objects.count()
        == 0
    )
    catalog_data[3].available = False
    catalog_data[3].save()
    assert post_with_csrf(client, "/api/v1/public/orders/", body).status_code == 400
    assert ServiceSession.objects.count() == 0


def test_order_input_and_participants_are_resource_scoped(point_data, catalog_data, identity_data):
    client = customer(point_data[1])
    body = payload(catalog_data)
    for extra in ("price", "closed", "unit_id", "staff_id", "status", "session_id"):
        assert (
            post_with_csrf(
                client, "/api/v1/public/orders/", {**body, extra: "injected"}
            ).status_code
            == 400
        )
    other = ServiceSession.objects.create(unit=identity_data[3][0].unit)
    participant = SessionParticipant.objects.create(session=other, display_name="Foreign")
    foreign = {
        **body,
        "items": [
            {**body["items"][0], "participant_name": "", "participant_id": str(participant.id)}
        ],
    }
    assert post_with_csrf(client, "/api/v1/public/orders/", foreign).status_code == 400
    assert ServiceSession.objects.count() == 1
    admin = owner_client(identity_data)
    assert admin.get(f"/api/v1/staff/sessions/{other.id}/orders/").status_code == 404
    assert (
        post_with_csrf(
            client, "/api/v1/staff/orders/", {"point_id": str(point_data[0].id), **body}
        ).status_code
        == 401
    )


@pytest.mark.django_db(transaction=True)
def test_two_initial_orders_commit_to_one_session_and_duplicate_key_creates_one_batch(
    point_data, catalog_data
):
    customer(point_data[1])
    customer(point_data[1])
    devices = list(DeviceAccess.objects.filter(point=point_data[0]).order_by("id"))
    barrier = Barrier(2)
    body = payload(catalog_data)
    serializer = OrderInput(data=body)
    serializer.is_valid(raise_exception=True)

    def send(device):
        close_old_connections()
        barrier.wait(timeout=10)
        try:
            return submit_order(device, serializer.validated_data)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, devices))
    assert ServiceSession.objects.count() == 1 and OrderBatch.objects.count() == 2
    assert len({result["batch"]["session_id"] for result in results}) == 1
    barrier.reset()
    next_serializer = OrderInput(data=payload(catalog_data))
    next_serializer.is_valid(raise_exception=True)
    serializer = next_serializer
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, [devices[0], devices[0]]))
    assert json.loads(json.dumps(results[0], default=str)) == json.loads(
        json.dumps(results[1], default=str)
    )
    assert OrderBatch.objects.count() == 3


def test_database_rejects_cross_unit_session_point_and_wrong_bill_amount(
    point_data, catalog_data, identity_data
):
    client = customer(point_data[1])
    assert (
        post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    item = OrderItem.objects.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.filter(id=item.id).update(line_total=Decimal("0.01"))
    foreign = ServiceSession.objects.create(unit=identity_data[3][0].unit)
    with pytest.raises(IntegrityError), transaction.atomic():
        SessionPoint.objects.filter(session=item.batch.session).update(session=foreign)
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_manual_order_uses_staff_identity_and_checks_fresh_effective_grant(
    point_data, catalog_data, identity_data
):
    staff = pin_client()
    body = {"point_id": str(point_data[0].id), **payload(catalog_data)}
    receipt = post_with_csrf(staff, "/api/v1/staff/orders/", body)
    assert receipt.status_code == 201, receipt.content
    batch = OrderBatch.objects.get()
    assert batch.staff_id == identity_data[2].id and batch.device_id is None
    assert post_with_csrf(staff, "/api/v1/staff/orders/", body).json() == receipt.json()
    identity_data[2].permissions.clear()
    assert post_with_csrf(staff, "/api/v1/staff/orders/", body).status_code == 403
    assert OrderBatch.objects.count() == 1

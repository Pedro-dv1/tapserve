import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone

from apps.access.models import DeviceAccess
from apps.identity.authentication import StaffIdentity
from apps.identity.models import AuditEvent
from apps.orders.interventions import ItemCommand, change_item
from apps.orders.models import OrderItem, ProductionAssignment, ServiceSession
from apps.orders.production import StatusInput, transition
from common.idempotency import Conflict
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload
from tests.test_production import mutate, status_body


def edit(client, item, body):
    token = client.get("/api/v1/csrf/").json()["csrf_token"]
    return client.patch(
        f"/api/v1/public/items/{item.id}/",
        body,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )


def command(item):
    item.refresh_from_db()
    return {"idempotency_key": str(uuid.uuid4()), "expected_version": item.version}


def test_customer_edits_own_items_with_repricing_history_and_idempotence(point_data, catalog_data):
    client, other = customer(point_data[1]), customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    body = {
        **command(item),
        "quantity": 3,
        "option_ids": [str(catalog_data[5].id)],
        "notes": "Sem sal",
    }
    assert edit(other, item, body).status_code == 404
    assert edit(client, item, {**body, "unit_price": "0.01"}).status_code == 400
    changed = edit(client, item, body)
    assert changed.status_code == 200 and changed.json()["line_total"] == "37.05"
    assert edit(client, item, body).json() == changed.json()
    assert edit(client, item, {**body, "quantity": 4}).status_code == 409
    history = AuditEvent.objects.get(action="ITEM_EDIT")
    assert history.device_id == DeviceAccess.objects.order_by("issued_at").first().id
    assert history.details["before"]["line_total"] == "24.70"
    assert history.details["after"]["line_total"] == "37.05"
    assert history.details["before"]["notes"] == "Sem pimenta"
    assert history.details["after"]["notes"] == "Sem sal"
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditEvent.objects.filter(id=history.id).update(details={})
    assert (
        client.get("/api/v1/public/orders/").json()["results"][0]["items"][0]["can_customer_change"]
        is True
    )
    assert (
        other.get("/api/v1/public/orders/").json()["results"][0]["items"][0]["can_customer_change"]
        is False
    )
    cancelled = post_with_csrf(client, f"/api/v1/public/items/{item.id}/cancel/", command(item))
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    item.refresh_from_db()
    assert item.line_total == Decimal("37.05") and ServiceSession.objects.count() == 1


def test_customer_window_and_production_state_require_staff_permission(
    point_data, catalog_data, identity_data
):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    url = f"/api/v1/public/items/{item.id}/cancel/"
    OrderItem.objects.filter(id=item.id).update(created_at=timezone.now() - timedelta(minutes=4))
    assert post_with_csrf(client, url, command(item)).status_code == 409
    OrderItem.objects.filter(id=item.id).update(created_at=timezone.now())
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    assert mutate(admin, item, "NEW", "ACCEPTED").status_code == 200
    assert (
        client.get("/api/v1/public/orders/").json()["results"][0]["items"][0]["can_customer_change"]
        is True
    )
    assert mutate(admin, item, "ACCEPTED", "PREPARING").status_code == 200
    assert post_with_csrf(client, url, command(item)).status_code == 409
    staff_url = f"/api/v1/staff/items/{item.id}/cancel/"
    assert (
        post_with_csrf(
            pin_client(), staff_url, {**command(item), "reason": "Cliente desistiu"}
        ).status_code
        == 403
    )
    assert (
        post_with_csrf(
            admin, staff_url, {**command(item), "reason": "Cliente desistiu"}
        ).status_code
        == 200
    )
    assert AuditEvent.objects.get(action="ITEM_CANCEL").reason == "Cliente desistiu"


def test_order_policy_is_strong_scoped_bounded_and_audited(identity_data):
    admin = owner_client(identity_data)
    url = "/api/v1/admin/order-policy/"
    assert pin_client().get(url).status_code == 403
    assert admin.get(url).json() == {
        "customer_edit_window_minutes": 3,
        "table_takeaway_enabled": False,
        "leftover_packaging_enabled": False,
        "public_pickup_enabled": False,
        "menu_layout": "EDITORIAL",
    }
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "expected_window_minutes": 3,
        "customer_edit_window_minutes": 0,
        "reason": "Desativar correções diretas",
    }
    assert (
        admin.put(
            url,
            {**body, "customer_edit_window_minutes": 61},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 400
    )
    assert (
        admin.put(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code
        == 200
    )
    assert (
        admin.put(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code
        == 200
    )
    assert AuditEvent.objects.filter(action="ORDER_POLICY_UPDATED").count() == 1
    identity_data[0].refresh_from_db()
    assert identity_data[0].customer_edit_window_minutes == 0
    assert identity_data[3][0].unit.customer_edit_window_minutes == 3


@pytest.mark.django_db(transaction=True)
def test_prepare_versus_customer_cancel_has_only_one_committed_winner(
    point_data, catalog_data, identity_data
):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    assert mutate(admin, item, "NEW", "ACCEPTED").status_code == 200
    device = DeviceAccess.objects.get()
    identity = StaffIdentity(
        identity_data[1],
        True,
        frozenset(identity_data[1].permissions.values_list("code", flat=True)),
    )
    cancel = ItemCommand(data=command(item))
    cancel.is_valid(raise_exception=True)
    prepare = StatusInput(data=status_body("ACCEPTED", "PREPARING"))
    prepare.is_valid(raise_exception=True)
    barrier = Barrier(2)

    def act(action):
        close_old_connections()
        barrier.wait(timeout=10)
        try:
            if action == "cancel":
                change_item(device, item.id, cancel.validated_data, cancel=True)
            else:
                transition(identity, item.id, prepare.validated_data)
            return True
        except Conflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(act, ["cancel", "prepare"]))
    assert results.count(True) == results.count(False) == 1
    item.refresh_from_db()
    assert item.status in {"PREPARING", "CANCELLED"}

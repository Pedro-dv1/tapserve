import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.catalog.models import Product, ProductionSector
from apps.identity.authentication import StaffIdentity
from apps.orders.models import DomainEvent, ItemStatusEvent, OrderItem, ProductionAssignment
from apps.orders.production import StatusInput, transition
from common.idempotency import Conflict
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload


def status_body(expected, target):
    return {"idempotency_key": str(uuid.uuid4()), "expected_status": expected, "status": target}


def mutate(client, item, expected, target):
    return post_with_csrf(
        client, f"/api/v1/staff/items/{item.id}/status/", status_body(expected, target)
    )


def test_production_sector_scope_partial_completion_and_delivery_ownership(
    point_data, catalog_data, identity_data
):
    bar = ProductionSector.objects.create(unit=identity_data[0], name="Bar")
    drink = Product.objects.create(
        unit=identity_data[0],
        category=catalog_data[1],
        production_sector=bar,
        name="Suco",
        base_price=Decimal("5.00"),
    )
    body = payload(catalog_data)
    body["items"].append({"product_id": str(drink.id), "quantity": 1, "option_ids": []})
    device = customer(point_data[1])
    receipt = post_with_csrf(device, "/api/v1/public/orders/", body).json()
    first, second = OrderItem.objects.order_by("created_at", "id")
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    response = admin.get("/api/v1/staff/production/items/")
    assert response.status_code == 200 and {row["id"] for row in response.json()["results"]} == {
        str(first.id),
        str(second.id),
    }
    assert response.json()["results"][0]["point_names"] == ["Mesa 07"]
    assert admin.get(f"/api/v1/staff/production/items/?sector={bar.id}").status_code == 200
    assert mutate(admin, first, "NEW", "READY").status_code == 409
    first_body = status_body("NEW", "ACCEPTED")
    first_url = f"/api/v1/staff/items/{first.id}/status/"
    accepted = post_with_csrf(admin, first_url, first_body)
    assert accepted.status_code == 200
    assert post_with_csrf(admin, first_url, first_body).json() == accepted.json()
    assert mutate(admin, first, "ACCEPTED", "PREPARING").status_code == 200
    assert mutate(admin, first, "PREPARING", "READY").status_code == 200
    assert device.get("/api/v1/public/orders/").json()["results"][0]["all_ready"] is False
    waiter = pin_client()
    assert mutate(waiter, first, "READY", "DELIVERING").status_code == 200
    assert mutate(admin, first, "DELIVERING", "DELIVERED").status_code == 403
    assert mutate(waiter, first, "DELIVERING", "DELIVERED").status_code == 200
    assert ItemStatusEvent.objects.count() == 5 and DomainEvent.objects.count() == 6
    assert device.get("/api/v1/public/orders/").json()["results"][0]["id"] == receipt["batch"]["id"]
    assert mutate(Client(enforce_csrf_checks=True), first, "DELIVERED", "READY").status_code == 401
    event = ItemStatusEvent.objects.first()
    with pytest.raises(IntegrityError), transaction.atomic():
        ItemStatusEvent.objects.filter(id=event.id).update(status="NEW")
    ProductionAssignment.objects.create(staff=identity_data[1], sector=bar)
    for before, after in (("NEW", "ACCEPTED"), ("ACCEPTED", "PREPARING"), ("PREPARING", "READY")):
        assert mutate(admin, second, before, after).status_code == 200
    assert device.get("/api/v1/public/orders/").json()["results"][0]["all_ready"] is True


def test_production_page_does_not_query_unit_once_per_item(point_data, catalog_data, identity_data):
    client = customer(point_data[1])
    body = payload(catalog_data)
    body["items"] *= 20
    assert post_with_csrf(client, "/api/v1/public/orders/", body).status_code == 201
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    with CaptureQueriesContext(connection) as queries:
        response = admin.get("/api/v1/staff/production/items/")
    assert response.status_code == 200 and response.json()["count"] == 20
    # Includes fresh auth/grant checks, pagination and point prefetch; not 20 extra Unit reads.
    assert len(queries) <= 20, len(queries)


def test_production_assignment_foreign_units_and_mass_assignment_are_rejected(
    point_data, catalog_data, identity_data
):
    admin = owner_client(identity_data)
    foreign_sector = ProductionSector.objects.create(unit=identity_data[3][0].unit, name="Foreign")
    url = f"/api/v1/admin/staff/{identity_data[2].id}/sectors/"
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    assert (
        admin.put(
            url,
            {"sector_ids": [str(foreign_sector.id)], "reason": "test"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 400
    )
    assert (
        admin.put(
            url,
            {"sector_ids": [str(catalog_data[2].id)], "reason": "test"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )
    assert admin.get(url).json()["sector_ids"] == [str(catalog_data[2].id)]
    assert admin.get(f"/api/v1/admin/staff/{identity_data[3][0].id}/sectors/").status_code == 404
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductionAssignment.objects.create(staff=identity_data[2], sector=foreign_sector)
    assert pin_client().get("/api/v1/staff/production/items/").status_code == 403
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    assert (
        post_with_csrf(
            admin,
            f"/api/v1/staff/items/{item.id}/status/",
            {**status_body("NEW", "ACCEPTED"), "price": "0.01"},
        ).status_code
        == 400
    )


@pytest.mark.django_db(transaction=True)
def test_two_waiters_cannot_claim_the_same_ready_item(point_data, catalog_data, identity_data):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    for before, after in (("NEW", "ACCEPTED"), ("ACCEPTED", "PREPARING"), ("PREPARING", "READY")):
        assert mutate(admin, item, before, after).status_code == 200
    actors = [
        StaffIdentity(staff, strong, frozenset(staff.permissions.values_list("code", flat=True)))
        for staff, strong in ((identity_data[1], True), (identity_data[2], False))
    ]
    barrier = Barrier(2)

    def claim(actor):
        close_old_connections()
        data = StatusInput(data=status_body("READY", "DELIVERING"))
        data.is_valid(raise_exception=True)
        barrier.wait(timeout=10)
        try:
            transition(actor, item.id, data.validated_data)
            return True
        except Conflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, actors))
    assert results.count(True) == results.count(False) == 1
    assert ItemStatusEvent.objects.filter(status="DELIVERING").count() == 1
    item.refresh_from_db()
    assert item.status == "DELIVERING" and item.delivered_by_id in {
        actor.staff.id for actor in actors
    }

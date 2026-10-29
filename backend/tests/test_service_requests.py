import asyncio
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from channels.db import database_sync_to_async
from django.db import IntegrityError, close_old_connections, transaction

from apps.access.models import ServicePoint
from apps.access.services import cipher, digest
from apps.identity.authentication import StaffIdentity
from apps.identity.models import AuditEvent
from apps.orders.models import DomainEvent, ServiceRequest, ServiceSession
from apps.orders.service_requests import StaffRequestCommand, change_request
from common.idempotency import Conflict
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload
from tests.test_realtime import socket


def call_body(kind="ATTENDANT"):
    return {"idempotency_key": str(uuid.uuid4()), "kind": kind}


def status_body(status, expected="OPEN"):
    return {"idempotency_key": str(uuid.uuid4()), "expected_status": expected, "status": status}


def test_calls_on_free_point_are_idempotent_then_join_first_occupation(
    point_data, catalog_data, identity_data
):
    client, another = customer(point_data[1]), customer(point_data[1])
    body = call_body()
    opened = post_with_csrf(client, "/api/v1/public/service-requests/", body)
    assert opened.status_code == 201 and opened.json()["session_id"] is None
    assert ServiceSession.objects.count() == 0
    assert post_with_csrf(client, "/api/v1/public/service-requests/", body).json() == opened.json()
    assert (
        post_with_csrf(another, "/api/v1/public/service-requests/", call_body()).status_code == 409
    )
    assert (
        post_with_csrf(client, "/api/v1/public/service-requests/", call_body("OTHER")).status_code
        == 400
    )
    assert (
        post_with_csrf(
            client,
            "/api/v1/public/service-requests/",
            {**call_body("NAPKIN"), "unit_id": str(identity_data[3][0].unit_id)},
        ).status_code
        == 400
    )
    assert client.get("/api/v1/public/service-requests/").json()["count"] == 1
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    call = ServiceRequest.objects.get()
    assert call.session_id == ServiceSession.objects.get().id
    cancel_url = f"/api/v1/public/service-requests/{call.id}/cancel/"
    assert (
        post_with_csrf(
            another, cancel_url, {"idempotency_key": str(uuid.uuid4()), "expected_status": "OPEN"}
        ).status_code
        == 404
    )
    waiter, owner = pin_client(), owner_client(identity_data)
    url = f"/api/v1/staff/service-requests/{call.id}/status/"
    assigned = post_with_csrf(waiter, url, status_body("ASSIGNED"))
    assert assigned.status_code == 200 and assigned.json()["assignee_name"] == "Waiter"
    assert post_with_csrf(owner, url, status_body("RESOLVED", "ASSIGNED")).status_code == 403
    assert post_with_csrf(waiter, url, status_body("RESOLVED", "ASSIGNED")).status_code == 200
    assert client.get("/api/v1/public/service-requests/").json()["count"] == 0
    assert AuditEvent.objects.filter(action="CALL_RESOLVED").count() == 1
    foreign = identity_data[3][0]
    with pytest.raises(IntegrityError), transaction.atomic():
        ServiceRequest.objects.filter(id=call.id).update(assigned_to=foreign)


@pytest.mark.django_db(transaction=True)
def test_call_claim_race_yields_one_responsible_staff(point_data, identity_data):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/service-requests/", call_body())
    call = ServiceRequest.objects.get()
    actors = [
        StaffIdentity(staff, strong, frozenset(staff.permissions.values_list("code", flat=True)))
        for staff, strong in ((identity_data[1], True), (identity_data[2], False))
    ]
    data = StaffRequestCommand(data=status_body("ASSIGNED"))
    data.is_valid(raise_exception=True)
    barrier = Barrier(2)

    def claim(actor):
        close_old_connections()
        barrier.wait(timeout=10)
        try:
            change_request(actor, call.id, data.validated_data, manual=True)
            return True
        except Conflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, actors))
    assert results.count(True) == results.count(False) == 1
    assert AuditEvent.objects.filter(action="CALL_ASSIGNED").count() == 1
    call.refresh_from_db()
    assert call.assigned_to_id in {actor.staff.id for actor in actors}


@pytest.mark.django_db(transaction=True)
def test_free_point_notifications_do_not_leak_to_other_free_point_or_rollback(
    point_data, identity_data
):
    token = secrets.token_urlsafe(32)
    ServicePoint.objects.create(
        unit=identity_data[0],
        name="Mesa 08",
        type="TABLE",
        number=8,
        token_digest=digest(token),
        token_ciphertext=cipher().encrypt(token.encode()),
    )
    own, other = customer(point_data[1]), customer(token)

    async def scenario():
        first, second = socket(own, "/ws/v1/public/"), socket(other, "/ws/v1/public/")
        try:
            for connection in (first, second):
                assert (await connection.connect(timeout=10))[0]
                await connection.receive_json_from(timeout=10)
            response = await database_sync_to_async(post_with_csrf)(
                own, "/api/v1/public/service-requests/", call_body()
            )
            assert response.status_code == 201
            assert (await first.receive_json_from(timeout=10))["kind"] == "CALL_OPENED"
            assert await second.receive_nothing(timeout=0.2)

            def rollback():
                from apps.orders.production import publish

                with pytest.raises(ValueError), transaction.atomic():
                    publish(None, "ROLLED_BACK", [], point=point_data[0])
                    raise ValueError("Rollback")

            await database_sync_to_async(rollback)()
            assert await first.receive_nothing(timeout=0.2)
            assert await second.receive_nothing(timeout=0.2)
        finally:
            await first.disconnect()
            await second.disconnect()

    asyncio.run(scenario())
    assert DomainEvent.objects.filter(kind="ROLLED_BACK").count() == 0
    assert ServiceSession.objects.count() == 0

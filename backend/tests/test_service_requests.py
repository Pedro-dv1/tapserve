import asyncio
import json
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from channels.db import database_sync_to_async
from django.db import IntegrityError, close_old_connections, transaction
from rest_framework.renderers import JSONRenderer

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
from tests.test_realtime import assert_no_refresh, next_message, socket


def call_body(kind="ATTENDANT"):
    return {"idempotency_key": str(uuid.uuid4()), "kind": kind}


def status_body(status, expected="OPEN"):
    return {"idempotency_key": str(uuid.uuid4()), "expected_status": expected, "status": status}


@pytest.mark.parametrize("reason", [None, "", "Talheres já recebidos", "x" * 300])
def test_public_cancellation_preserves_optional_reason_and_replay(point_data, reason):
    client, other = customer(point_data[1]), customer(point_data[1])
    opened = post_with_csrf(client, "/api/v1/public/service-requests/", call_body("CUTLERY"))
    assert opened.status_code == 201
    identifier = opened.json()["id"]
    url = f"/api/v1/public/service-requests/{identifier}/cancel/"
    body = {"idempotency_key": str(uuid.uuid4()), "expected_status": "OPEN"}
    if reason is not None:
        body["reason"] = reason
    assert post_with_csrf(other, url, body).status_code == 404
    response = post_with_csrf(client, url, body)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert post_with_csrf(client, url, body).json() == response.json()
    audit = AuditEvent.objects.get(action="CALL_CANCELLED", resource_id=identifier)
    assert audit.reason == (reason or "")
    assert audit.device_id == ServiceRequest.objects.get(id=identifier).device_id
    assert audit.staff_id is None
    assert audit.details["before"] == "OPEN" and audit.details["after"] == "CANCELLED"
    assert ServiceRequest.objects.get(id=identifier).status == "CANCELLED"
    assert post_with_csrf(client, url, {**body, "reason": "outro motivo"}).status_code == 409
    assert AuditEvent.objects.filter(action="CALL_CANCELLED", resource_id=identifier).count() == 1


@pytest.mark.parametrize("extra", [{"reason": "x" * 301}, {"reason": None}, {"reason": []}, {"status": "RESOLVED"}])
def test_public_cancellation_rejects_invalid_reason_without_side_effects(point_data, extra):
    client = customer(point_data[1])
    opened = post_with_csrf(client, "/api/v1/public/service-requests/", call_body("CUTLERY"))
    identifier = opened.json()["id"]
    response = post_with_csrf(client, f"/api/v1/public/service-requests/{identifier}/cancel/", {
        "idempotency_key": str(uuid.uuid4()), "expected_status": "OPEN", **extra,
    })
    assert response.status_code == 400
    assert ServiceRequest.objects.get(id=identifier).status == "OPEN"
    assert not AuditEvent.objects.filter(action="CALL_CANCELLED", resource_id=identifier).exists()


def test_public_cancellation_replays_receipt_from_before_optional_reason(point_data):
    client = customer(point_data[1])
    opened = post_with_csrf(client, "/api/v1/public/service-requests/", call_body("CUTLERY"))
    call = ServiceRequest.objects.get(id=opened.json()["id"])
    legacy = {"idempotency_key": uuid.uuid4(), "expected_status": "OPEN"}
    previous = change_request(call.device, call.id, legacy)
    response = post_with_csrf(client, f"/api/v1/public/service-requests/{call.id}/cancel/", {
        **legacy, "idempotency_key": str(legacy["idempotency_key"]),
    })
    assert response.status_code == 200 and response.json() == json.loads(JSONRenderer().render(previous))
    assert AuditEvent.objects.filter(action="CALL_CANCELLED", resource_id=str(call.id)).count() == 1


@pytest.mark.django_db(transaction=True)
def test_public_cancellation_reason_over_real_http(point_data, live_server):
    client = customer(point_data[1])
    opened = post_with_csrf(client, "/api/v1/public/service-requests/", call_body("CUTLERY"))
    identifier = opened.json()["id"]
    csrf = client.get("/api/v1/csrf/").json()["csrf_token"]
    assert live_server.url.startswith(("http://localhost:", "http://127.0.0.1:"))
    body = {"idempotency_key": str(uuid.uuid4()), "expected_status": "OPEN", "reason": "Talheres recebidos via HTTP"}
    request = Request(  # noqa: S310 - exclusively pytest-owned loopback server.
        live_server.url + f"/api/v1/public/service-requests/{identifier}/cancel/",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf,
                 "Cookie": "; ".join(f"{name}={item.value}" for name, item in client.cookies.items())},
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310 - pytest-owned loopback only.
        assert response.status == 200 and json.loads(response.read())["status"] == "CANCELLED"
    assert AuditEvent.objects.get(action="CALL_CANCELLED", resource_id=identifier).reason == body["reason"]
    assert ServiceRequest.objects.get(id=identifier).status == "CANCELLED"
    request.remove_header("X-csrftoken")
    with pytest.raises(HTTPError) as denied:
        urlopen(request, timeout=15)  # noqa: S310 - same pytest server; exercise CSRF.
    assert denied.value.code == 403


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
                assert (await next_message(connection))["kind"] == "SNAPSHOT_REQUIRED"
            response = await database_sync_to_async(post_with_csrf)(
                own, "/api/v1/public/service-requests/", call_body()
            )
            assert response.status_code == 201
            assert (await next_message(first))["kind"] == "CALL_OPENED"
            await assert_no_refresh(second)

            def rollback():
                from apps.orders.production import publish

                with pytest.raises(ValueError), transaction.atomic():
                    publish(None, "ROLLED_BACK", [], point=point_data[0])
                    raise ValueError("Rollback")

            await database_sync_to_async(rollback)()
            await assert_no_refresh(first)
            await assert_no_refresh(second)
        finally:
            await first.disconnect()
            await second.disconnect()

    asyncio.run(scenario())
    assert DomainEvent.objects.filter(kind="ROLLED_BACK").count() == 0
    assert ServiceSession.objects.count() == 0

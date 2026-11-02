import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client
from rest_framework.exceptions import APIException

from apps.access.models import DeviceAccess
from apps.identity.authentication import StaffIdentity
from apps.identity.models import AuditEvent, Permission
from apps.orders.models import (
    ExternalReceipt,
    OrderItem,
    ServiceRequest,
    ServiceSession,
    SessionLifecycleEvent,
    SessionParticipant,
    SessionPoint,
)
from apps.orders.settlement import ExternalReceiptInput, change_settlement
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload


@pytest.mark.django_db(transaction=True)
def test_closing_session_disconnects_existing_customer_websocket(
    point_data, catalog_data, identity_data
):
    from channels.db import database_sync_to_async

    from tests.test_realtime import next_message, socket

    client, admin, session = open_session(point_data, catalog_data, identity_data)
    assert receipt(admin, session, point_data[0]).status_code == 200
    body = command(session, reason="Synthetic closure for socket revocation")

    async def scenario():
        public = socket(client, "/ws/v1/public/")
        try:
            assert (await public.connect(timeout=10))[0]
            assert (await next_message(public))["kind"] == "SNAPSHOT_REQUIRED"
            result = await database_sync_to_async(post_with_csrf)(
                admin, f"/api/v1/staff/sessions/{session.id}/close/", body
            )
            assert result.status_code == 200
            closed = await next_message(public, closing=True)
            assert closed["type"] == "websocket.close" and closed["code"] == 4401
        finally:
            await public.disconnect()

    asyncio.run(scenario())


def command(session, **extra):
    session.refresh_from_db()
    return {"idempotency_key": str(uuid.uuid4()), "expected_version": session.version, **extra}


def open_session(point_data, catalog_data, identity_data, *, deliver=True):
    client = customer(point_data[1])
    response = post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    assert response.status_code == 201, response.content
    session = ServiceSession.objects.get(id=response.json()["batch"]["session_id"])
    admin = owner_client(identity_data)
    if deliver:
        item = OrderItem.objects.get(batch__session=session)
        previous = "NEW"
        for state in ["ACCEPTED", "PREPARING", "READY", "DELIVERING", "DELIVERED"]:
            result = post_with_csrf(
                admin,
                f"/api/v1/staff/items/{item.id}/status/",
                {
                    "idempotency_key": str(uuid.uuid4()),
                    "expected_status": previous,
                    "status": state,
                },
            )
            assert result.status_code == 200, result.content
            previous = state
    session.refresh_from_db()
    return client, admin, session


def receipt(admin, session, point, amount="24.70", **extra):
    return post_with_csrf(
        admin,
        f"/api/v1/staff/sessions/{session.id}/external-receipts/",
        command(
            session,
            point_id=str(point.id),
            amount=amount,
            method="CARD",
            **extra,
        ),
    )


@pytest.mark.django_db(transaction=True)
def test_complete_closure_and_next_party_never_share_history(
    point_data, catalog_data, identity_data
):
    old_client, admin, session = open_session(point_data, catalog_data, identity_data)
    first_participant = SessionParticipant.objects.get(session=session)
    called = post_with_csrf(
        old_client,
        "/api/v1/public/service-requests/",
        {
            "idempotency_key": str(uuid.uuid4()),
            "kind": "CHECK",
        },
    )
    assert called.status_code == 201
    assert receipt(admin, session, point_data[0], "10.00").status_code == 200
    summary = admin.get(f"/api/v1/staff/sessions/{session.id}/settlement/").json()
    assert summary["consumption_total"] == "24.70" and summary["remaining"] == "14.70"
    blocked = post_with_csrf(admin, f"/api/v1/staff/sessions/{session.id}/close/", command(session))
    assert blocked.status_code == 409
    assert receipt(admin, session, point_data[0], "14.70").status_code == 200
    close_command = command(session, reason="Recebimento externo declarado pela equipe.")
    closed = post_with_csrf(admin, f"/api/v1/staff/sessions/{session.id}/close/", close_command)
    assert closed.status_code == 200, closed.content
    assert closed.json()["status"] == "CLOSED"
    retry = post_with_csrf(admin, f"/api/v1/staff/sessions/{session.id}/close/", close_command)
    assert retry.json() == closed.json()
    assert SessionLifecycleEvent.objects.filter(session=session, action="CLOSE").count() == 1
    assert not SessionPoint.objects.filter(session=session, ended_at__isnull=True).exists()
    assert not DeviceAccess.objects.filter(session=session, revoked_at__isnull=True).exists()
    assert not ServiceRequest.objects.filter(
        session=session, status__in=["OPEN", "ASSIGNED"]
    ).exists()
    assert receipt(admin, session, point_data[0], "1.00").status_code == 409
    old_item = OrderItem.objects.get(batch__session=session)
    assert (
        post_with_csrf(
            admin,
            f"/api/v1/staff/items/{old_item.id}/cancel/",
            {"idempotency_key": str(uuid.uuid4()), "expected_version": old_item.version},
        ).status_code
        == 409
    )
    assert old_client.get("/api/v1/public/context/").status_code == 401
    assert (
        post_with_csrf(old_client, "/api/v1/public/orders/", payload(catalog_data)).status_code
        == 401
    )
    fresh_client = customer(point_data[1])
    assert fresh_client.get("/api/v1/public/session/").json()["session"] is None
    assert fresh_client.get("/api/v1/public/orders/").json()["results"] == []
    result = post_with_csrf(fresh_client, "/api/v1/public/orders/", payload(catalog_data))
    assert result.status_code == 201, result.content
    next_id = result.json()["batch"]["session_id"]
    assert next_id != str(session.id)
    assert not SessionParticipant.objects.filter(
        session_id=next_id, id=first_participant.id
    ).exists()
    assert admin.get(f"/api/v1/staff/sessions/{session.id}/orders/").json()["count"] == 1
    history = admin.get(f"/api/v1/staff/tables/{point_data[0].id}/history/").json()
    assert {r["id"] for r in history["results"]} == {str(session.id), next_id}
    denied = post_with_csrf(
        admin, f"/api/v1/staff/sessions/{session.id}/reopen/", command(session, reason="Continuar")
    )
    assert denied.status_code == 409


@pytest.mark.django_db
def test_external_receipts_enforce_grants_scope_values_and_replay(
    point_data, catalog_data, identity_data
):
    public, admin, session = open_session(point_data, catalog_data, identity_data)
    url = f"/api/v1/staff/sessions/{session.id}/external-receipts/"
    body = command(session, point_id=str(point_data[0].id), amount="10.00", method="PIX")
    for unauthorized in [public, Client(enforce_csrf_checks=True), pin_client()]:
        assert post_with_csrf(unauthorized, url, body).status_code in {401, 403}
    for amount in ["0.00", "-1.00", "NaN", "10.001"]:
        assert post_with_csrf(admin, url, {**body, "amount": amount}).status_code == 400
    assert post_with_csrf(admin, url, {**body, "amount": "24.71"}).status_code == 409
    assert post_with_csrf(admin, url, {**body, "total": "0.00"}).status_code == 400
    first = post_with_csrf(admin, url, body)
    assert first.status_code == 200
    assert post_with_csrf(admin, url, body).json() == first.json()
    assert post_with_csrf(admin, url, {**body, "amount": "9.00"}).status_code == 409
    assert ExternalReceipt.objects.filter(session=session).count() == 1
    result_url = f"/api/v1/staff/sessions/{session.id}/settlement-results/{body['idempotency_key']}/?action=RECEIPT"
    assert admin.get(result_url).json()["result"] == first.json()
    assert admin.get(result_url).json()["applied"] is True
    for staff in identity_data[3]:
        codes = ["VIEW_OPERATION", "VIEW_ALL_TABLES", "REGISTER_PAYMENT"]
        staff.permissions.set(Permission.objects.filter(code__in=codes))
        identity = StaffIdentity(staff, False, frozenset(codes))
        serializer = ExternalReceiptInput(data=body)
        assert serializer.is_valid(), serializer.errors
        with pytest.raises(APIException) as error:
            change_settlement(identity, session.id, serializer.validated_data, "RECEIPT")
        assert error.value.status_code == 404


@pytest.mark.django_db
def test_closure_requires_final_items_and_receipt_corrections_are_append_only(
    point_data, catalog_data, identity_data
):
    _, admin, session = open_session(point_data, catalog_data, identity_data, deliver=False)
    assert receipt(admin, session, point_data[0]).status_code == 200
    denied = post_with_csrf(admin, f"/api/v1/staff/sessions/{session.id}/close/", command(session))
    assert denied.status_code == 409
    original = ExternalReceipt.objects.get(session=session)
    reverse_url = f"/api/v1/staff/sessions/{session.id}/external-receipts/{original.id}/reverse/"
    reverse = command(session, reason="Forma declarada incorretamente.")
    result = post_with_csrf(admin, reverse_url, reverse)
    assert result.status_code == 200, result.content
    assert result.json()["declared_received"] == "0.00"
    assert post_with_csrf(admin, reverse_url, reverse).json() == result.json()
    assert (
        post_with_csrf(admin, reverse_url, command(session, reason="Dupla reversão")).status_code
        == 409
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ExternalReceipt.objects.filter(id=original.id).update(amount=Decimal("1.00"))
    with pytest.raises(IntegrityError), transaction.atomic():
        ExternalReceipt.objects.filter(id=original.id).delete()
    assert receipt(admin, session, point_data[0]).status_code == 200
    assert ExternalReceipt.objects.filter(session=session).count() == 3


@pytest.mark.django_db
def test_reopen_retains_closed_snapshots_and_never_restores_old_devices(
    point_data, catalog_data, identity_data
):
    public, admin, session = open_session(point_data, catalog_data, identity_data)
    receipt(admin, session, point_data[0])
    closed = post_with_csrf(admin, f"/api/v1/staff/sessions/{session.id}/close/", command(session))
    assert closed.status_code == 200
    snapshot = SessionLifecycleEvent.objects.get(session=session)
    old_links = list(SessionPoint.objects.filter(session=session).values_list("id", flat=True))
    reopened = post_with_csrf(
        admin,
        f"/api/v1/staff/sessions/{session.id}/reopen/",
        command(session, reason="Mesmo grupo retomou o atendimento."),
    )
    assert reopened.status_code == 200, reopened.content
    assert reopened.json()["status"] == "REOPENED"
    snapshot.refresh_from_db()
    assert snapshot.action == "CLOSE" and snapshot.consumption_total == Decimal("24.70")
    assert not SessionPoint.objects.filter(id__in=old_links, ended_at__isnull=True).exists()
    assert SessionPoint.objects.filter(session=session, ended_at__isnull=True).count() == 1
    assert public.get("/api/v1/public/context/").status_code == 401
    assert OrderItem.objects.get(batch__session=session).status == "DELIVERED"
    assert SessionLifecycleEvent.objects.filter(session=session).count() == 2
    with pytest.raises(IntegrityError), transaction.atomic():
        SessionLifecycleEvent.objects.filter(id=snapshot.id).update(reason="Apagar motivo")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("action", ["RECEIPT", "CLOSE"])
@pytest.mark.parametrize("same_key", [True, False])
def test_receipt_and_close_retries_are_serialized(
    point_data, catalog_data, identity_data, action, same_key
):
    _, admin, session = open_session(point_data, catalog_data, identity_data)
    if action == "CLOSE":
        assert receipt(admin, session, point_data[0]).status_code == 200
    session.refresh_from_db()
    staff = identity_data[1]
    identity = StaffIdentity(
        staff, True, frozenset(staff.permissions.values_list("code", flat=True))
    )
    body = {"idempotency_key": uuid.uuid4(), "expected_version": session.version, "reason": "teste"}
    if action == "RECEIPT":
        body.update(point_id=point_data[0].id, amount=Decimal("24.70"), method="MONEY")
    barrier = Barrier(2)

    def race(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            attempt = {
                **body,
                "idempotency_key": body["idempotency_key"]
                if same_key or index == 0
                else uuid.uuid4(),
            }
            try:
                return 200, change_settlement(identity, session.id, attempt, action)
            except APIException as error:
                return error.status_code, None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(race, range(2)))
    if same_key:
        assert results[0] == results[1]
        assert results[0][0] == 200
    else:
        assert sorted(result[0] for result in results) == [200, 409]
    if action == "RECEIPT":
        assert ExternalReceipt.objects.filter(session=session).count() == 1
    else:
        assert SessionLifecycleEvent.objects.filter(session=session, action="CLOSE").count() == 1
    assert (
        AuditEvent.objects.filter(
            resource_id=str(session.id), action="SETTLEMENT_" + action
        ).count()
        == 1
    )

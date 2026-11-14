"""Failure/revocation controls, independently of notification delivery health."""
import asyncio
import socket as network

import psycopg
import pytest
from channels.db import database_sync_to_async
from django.db import connection, transaction
from django.test import Client
from psycopg import sql

from apps.identity.models import Permission
from apps.orders import realtime
from apps.orders.models import DomainEvent, RealtimeLease
from apps.orders.production import publish
from tests.test_access import customer
from tests.test_identity import owner_client, post_with_csrf
from tests.test_mfa import password_login
from tests.test_orders import payload
from tests.test_realtime import next_message, socket

pytestmark = pytest.mark.django_db(transaction=True)


def test_committed_event_and_trigger_are_visible_on_independent_connection(
    point_data, catalog_data
):
    own = customer(point_data[1])
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    event = DomainEvent.objects.get(kind="ORDER_CREATED")
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_schema(), inet_server_port(), pg_backend_pid()")
        database, schema, port, sender_pid = cursor.fetchone()
    with psycopg.connect(**realtime.connection_parameters(), autocommit=True) as listener:
        assert listener.execute("SELECT current_database(), current_schema(), inet_server_port()").fetchone() == (database, schema, port)
        assert listener.info.backend_pid != sender_pid
        assert listener.execute("SELECT kind FROM orders_domainevent WHERE id=%s", (event.id,)).fetchone() == ("ORDER_CREATED",)
        assert listener.execute("SELECT tgenabled FROM pg_trigger WHERE tgrelid='orders_domainevent'::regclass AND tgname='domain_notify'").fetchone() == ("O",)
        function = listener.execute("SELECT pg_get_functiondef('tapserve_domain_notify()'::regprocedure)").fetchone()[0]
        assert "pg_notify" in function and "md5(TG_TABLE_SCHEMA)" in function
        channel = listener.execute("SELECT 'tapserve_events_' || md5(current_schema())").fetchone()[0]
        listener.execute(sql.SQL("LISTEN {}").format(sql.Identifier(channel)))
        assert listener.execute("SELECT pg_listening_channels()").fetchall() == [(channel,)]
        with pytest.raises(ValueError, match="synthetic rollback"), transaction.atomic():
            rolled_back = publish(None, "SYNTHETIC_ROLLBACK", [], point=point_data[0])
            raise ValueError("synthetic rollback")
        assert listener.execute("SELECT count(*) FROM orders_domainevent WHERE id=%s", (rolled_back.id,)).fetchone()[0] == 0


def test_listener_failure_is_logged_closed_and_next_connection_resubscribes(
    point_data, monkeypatch, caplog
):
    own = customer(point_data[1])

    async def unavailable(*args, **kwargs):
        raise psycopg.OperationalError("synthetic listener failure")

    async def scenario():
        failed = socket(own, "/ws/v1/public/")
        with monkeypatch.context() as patch:
            patch.setattr(realtime.psycopg.AsyncConnection, "connect", unavailable)
            try:
                assert await failed.connect(timeout=10) == (False, 1013)
            finally:
                await failed.disconnect()
        assert len(realtime.subscribers) == 0
        assert realtime.listener is None or realtime.listener.done()
        recovered = socket(own, "/ws/v1/public/")
        try:
            assert (await recovered.connect(timeout=10))[0]
            assert (await next_message(recovered))["kind"] == "SNAPSHOT_REQUIRED"
            assert len(realtime.subscribers) == 1
            assert not realtime.listener.done()
        finally:
            await recovered.disconnect()
        assert len(realtime.subscribers) == 0
        assert realtime.listener is None or realtime.listener.done()

    asyncio.run(scenario())
    assert "notification_listener_unavailable" in caplog.text
    assert RealtimeLease.objects.count() == 0


def test_partial_mfa_session_cannot_open_staff_websocket(identity_data):
    partial = Client(enforce_csrf_checks=True)
    assert password_login(partial, identity_data).json()["mfa_required"]

    async def scenario():
        connection = socket(partial, "/ws/v1/staff/")
        try:
            assert await connection.connect(timeout=10) == (False, 4401)
        finally:
            await connection.disconnect()

    asyncio.run(scenario())
    assert RealtimeLease.objects.count() == 0


def test_live_listener_disconnect_closes_sockets_and_reconnect_uses_one_subscription(
    point_data, monkeypatch, caplog
):
    own = customer(point_data[1])
    original_connect = realtime.psycopg.AsyncConnection.connect
    databases = []

    async def capture(*args, **kwargs):
        database = await original_connect(*args, **kwargs)
        databases.append(database)
        return database

    monkeypatch.setattr(realtime.psycopg.AsyncConnection, "connect", capture)

    async def scenario():
        for attempt in range(2):
            connection = socket(own, "/ws/v1/public/")
            try:
                assert (await connection.connect(timeout=10))[0]
                assert (await next_message(connection))["kind"] == "SNAPSHOT_REQUIRED"
                assert len(databases) == attempt + 1
                assert len(realtime.subscribers) == 1
                if attempt == 0:
                    # Simulate transport loss without closing a selector-registered handle.
                    transport = network.socket(fileno=databases[-1].fileno())
                    try:
                        transport.shutdown(network.SHUT_RDWR)
                    finally:
                        transport.detach()
                    closed = await next_message(connection, closing=True)
                    assert closed["type"] == "websocket.close" and closed["code"] == 1013
            finally:
                await connection.disconnect()
        assert all(database.closed for database in databases)
        assert len(realtime.subscribers) == 0

    asyncio.run(scenario())
    assert "notification_listener_unavailable" in caplog.text
    assert RealtimeLease.objects.count() == 0


def test_live_permission_revocation_denies_http_and_closes_staff_socket(identity_data):
    admin = owner_client(identity_data)

    def revoke():
        identity_data[1].permissions.remove(Permission.objects.get(code="VIEW_OPERATION"))
        assert admin.get("/api/v1/staff/tables/").status_code == 403

    async def scenario():
        connection = socket(admin, "/ws/v1/staff/")
        try:
            assert (await connection.connect(timeout=10))[0]
            assert (await next_message(connection))["kind"] == "SNAPSHOT_REQUIRED"
            await database_sync_to_async(revoke)()
            closed = await next_message(connection, closing=True)
            assert closed["type"] == "websocket.close" and closed["code"] == 4401
        finally:
            await connection.disconnect()

    asyncio.run(scenario())
    assert RealtimeLease.objects.count() == 0

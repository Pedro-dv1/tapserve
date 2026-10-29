import asyncio
import json
import secrets

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings

from apps.access.models import ServicePoint
from apps.access.services import cipher, digest
from apps.orders.models import ProductionAssignment, RealtimeLease, ServiceSession, SessionPoint
from config.asgi import application
from tests.test_access import customer
from tests.test_identity import owner_client, post_with_csrf
from tests.test_orders import payload
from tests.test_production import mutate


def socket(client, path, origin="http://testserver"):
    cookie = "; ".join(f"{name}={value.value}" for name, value in client.cookies.items())
    communicator = WebsocketCommunicator(
        application, path, headers=[(b"cookie", cookie.encode()), (b"origin", origin.encode())]
    )
    communicator.scope["client"] = ("127.0.0.1", 12345)
    return communicator


async def next_message(connection, *, closing=False):
    deadline = asyncio.get_running_loop().time() + 10
    while True:
        frame = await connection.receive_output(
            timeout=max(0.01, deadline - asyncio.get_running_loop().time())
        )
        if frame["type"] == "websocket.send":
            message = json.loads(frame["text"])
            if message == {"type": "heartbeat"}:
                await connection.send_json_to({"type": "heartbeat_ack"})
                continue
            if not closing:
                return message
        return frame


async def assert_no_refresh(connection):
    deadline = asyncio.get_running_loop().time() + 0.2
    while asyncio.get_running_loop().time() < deadline:
        if not await connection.receive_nothing(timeout=0.01):
            frame = await connection.receive_output(timeout=1)
            assert frame["type"] == "websocket.send"
            assert json.loads(frame["text"]) == {"type": "heartbeat"}
            await connection.send_json_to({"type": "heartbeat_ack"})


@pytest.mark.django_db(transaction=True)
def test_origin_tenant_revocation_reconnect_and_read_only_socket(
    point_data, catalog_data, identity_data
):
    own = customer(point_data[1])
    post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data))
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    token = secrets.token_urlsafe(32)
    other_point = ServicePoint.objects.create(
        unit=identity_data[3][0].unit,
        name="Other point",
        type="TABLE",
        number=1,
        token_digest=digest(token),
        token_ciphertext=cipher().encrypt(token.encode()),
    )
    other_session = ServiceSession.objects.create(unit=other_point.unit)
    SessionPoint.objects.create(session=other_session, point=other_point)
    other = customer(token)

    async def scenario():
        denied = socket(own, "/ws/v1/public/", "https://evil.example")
        assert (await denied.connect(timeout=10))[0] is False
        await denied.disconnect()
        query = socket(own, "/ws/v1/public/?token=forbidden")
        assert (await query.connect(timeout=10))[0] is False
        await query.disconnect()
        public, staff, foreign = (
            socket(own, "/ws/v1/public/"),
            socket(admin, "/ws/v1/staff/"),
            socket(other, "/ws/v1/public/"),
        )
        connected = []
        try:
            for connection in (public, staff, foreign):
                assert (await connection.connect(timeout=10))[0] is True
                connected.append(connection)
                assert (await next_message(connection))["kind"] == "SNAPSHOT_REQUIRED"
            response = await database_sync_to_async(post_with_csrf)(
                own, "/api/v1/public/orders/", payload(catalog_data)
            )
            assert response.status_code == 201
            event = await next_message(public)
            assert event["kind"] == "ORDER_CREATED" and event["event_id"] is not None
            assert await next_message(staff) == event
            await assert_no_refresh(foreign)
            # Reconnect never replays a mutation: it requests current authoritative state.
            await public.disconnect()
            connected.remove(public)
            public = socket(own, "/ws/v1/public/")
            assert (await public.connect(timeout=10))[0] is True
            connected.append(public)
            assert (await next_message(public))["kind"] == "SNAPSHOT_REQUIRED"
            from apps.orders.models import OrderItem

            item = await database_sync_to_async(
                lambda: OrderItem.objects.order_by("created_at").first()
            )()
            from apps.access.models import DeviceAccess

            device = await database_sync_to_async(
                lambda: DeviceAccess.objects.get(
                    token_digest=digest(own.cookies[settings.DEVICE_COOKIE_NAME].value)
                )
            )()
            assert (
                await database_sync_to_async(post_with_csrf)(
                    admin,
                    f"/api/v1/admin/device-access/{device.id}/revoke/",
                    {"reason": "test revocation"},
                )
            ).status_code == 204
            assert (
                await database_sync_to_async(mutate)(admin, item, "NEW", "ACCEPTED")
            ).status_code == 200
            assert (await next_message(public, closing=True))["type"] == "websocket.close"
            assert (await next_message(staff))["kind"] == "ITEM_STATUS_CHANGED"
            await staff.send_json_to({"unit_id": str(other_point.unit_id), "status": "DELIVERED"})
            assert (await next_message(staff, closing=True))["code"] == 4400
        finally:
            for connection in connected:
                await connection.disconnect()

    asyncio.run(scenario())
    assert RealtimeLease.objects.count() == 0

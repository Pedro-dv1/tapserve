"""One PostgreSQL listener per ASGI process; sockets receive scoped invalidations only."""

import asyncio
import json
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from http.cookies import SimpleCookie
from uuid import UUID, uuid4
from weakref import WeakSet

import psycopg
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.sessions.backends.db import SessionStore
from django.db import DatabaseError, transaction
from django.http import HttpRequest
from django.utils import timezone
from psycopg import sql
from rest_framework.exceptions import APIException

from apps.access.models import DeviceAccess
from apps.access.services import active_device
from apps.identity.authentication import resolve_staff
from apps.identity.services import rate_limit
from apps.organizations.models import Unit
from common.network import client_address

from .models import DomainEvent, RealtimeLease
from .production import assigned_sectors

logger = logging.getLogger("tapserve.realtime")
subscribers: WeakSet = WeakSet()
listener: asyncio.Task | None = None
listener_ready: asyncio.Event | None = None


@dataclass(frozen=True)
class Audience:
    unit_id: UUID
    actor: str
    session_id: UUID | None
    point_id: UUID | None
    all_tables: bool
    sectors: frozenset[str]

    def permits(self, event):
        return self.unit_id == event.unit_id and (
            # Catalog frames contain only an invalidation, never another point's data.
            event.kind == "CATALOG_CHANGED"
            or self.all_tables
            or (event.session_id is not None and self.session_id == event.session_id)
            or (event.point_id is not None and self.point_id == event.point_id)
            or bool(self.sectors.intersection(event.sector_ids))
        )


def audience(scope):
    cookies = SimpleCookie()
    for name, value in scope.get("headers", []):
        if name.lower() == b"cookie" and len(value) <= 8192:
            cookies.load(value.decode("latin1"))
    if scope["path"] == "/ws/v1/public/":
        cookie = cookies.get(settings.DEVICE_COOKIE_NAME)
        device = active_device(cookie.value if cookie else None)
        if device is None:
            return None
        return Audience(
            device.point.unit_id,
            "D:" + str(device.id),
            device.session_id,
            device.point_id,
            False,
            frozenset(),
        )
    cookie = cookies.get(settings.SESSION_COOKIE_NAME)
    session = SessionStore(session_key=cookie.value if cookie else None)
    request = HttpRequest()
    request.session = session
    identity = resolve_staff(session, get_user(request))
    if identity is None or not identity.allows("VIEW_OPERATION"):
        return None
    sectors = (
        frozenset(str(value) for value in assigned_sectors(identity))
        if identity.allows("UPDATE_PRODUCTION_STATUS")
        else frozenset()
    )
    if not identity.allows("VIEW_ALL_TABLES") and not sectors:
        return None
    return Audience(
        identity.staff.unit_id,
        "S:" + str(identity.staff.id),
        None,
        None,
        identity.allows("VIEW_ALL_TABLES"),
        sectors,
    )


def socket_meta(scope):
    request = HttpRequest()
    request.META.update(
        {
            "REMOTE_ADDR": (scope.get("client") or ("", 0))[0],
            "HTTP_X_TAPSERVE_CLIENT_IP": dict(scope.get("headers", []))
            .get(b"x-tapserve-client-ip", b"")
            .decode("latin1"),
        }
    )
    return request


def acquire(scope, current):
    rate_limit("socket-ip:" + client_address(socket_meta(scope)), 60, 60)
    rate_limit("socket-actor:" + current.actor, 10, 60)
    with transaction.atomic():
        Unit.objects.select_for_update().get(id=current.unit_id)
        RealtimeLease.objects.filter(
            unit_id=current.unit_id, expires_at__lte=timezone.now()
        ).delete()
        live = RealtimeLease.objects.filter(unit_id=current.unit_id, expires_at__gt=timezone.now())
        if live.count() >= 160 or live.filter(actor=current.actor).count() >= 2:
            return None
        return RealtimeLease.objects.create(
            unit_id=current.unit_id,
            actor=current.actor,
            expires_at=timezone.now() + timedelta(seconds=30),
        ).id


def renew(identifier):
    return (
        RealtimeLease.objects.filter(id=identifier, expires_at__gt=timezone.now()).update(
            expires_at=timezone.now() + timedelta(seconds=30), acknowledged=True
        )
        == 1
    )


def connection_parameters():
    database = settings.DATABASES["default"]
    return {
        "dbname": database["NAME"],
        "user": database["USER"],
        "password": database["PASSWORD"],
        "host": database["HOST"],
        "port": database["PORT"],
        **database["OPTIONS"],
    }


async def listen(ready):
    try:
        async with await psycopg.AsyncConnection.connect(
            autocommit=True, **connection_parameters()
        ) as database:
            cursor = await database.execute("SELECT 'tapserve_events_' || md5(current_schema())")
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("Notification schema not available")
            await database.execute(sql.SQL("LISTEN {}").format(sql.Identifier(row[0])))
            ready.set()
            async for notification in database.notifies():
                if not notification.payload.isdecimal() or len(notification.payload) > 20:
                    continue
                identifier = int(notification.payload)
                if identifier > 9223372036854775807:
                    continue
                event = await database_sync_to_async(
                    DomainEvent.objects.filter(id=identifier).first
                )()
                if event is not None:
                    for socket in list(subscribers):
                        try:
                            await socket.refresh(event)
                        except (TimeoutError, psycopg.Error, DatabaseError, OSError):
                            logger.error("socket_refresh_failed", extra={"error_type": "fanout"})
                            await socket.close(code=1013)
    except (TimeoutError, psycopg.Error, DatabaseError, OSError):
        logger.error("notification_listener_unavailable")
        for socket in list(subscribers):
            await socket.close(code=1013)
    finally:
        ready.set()


class DomainConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        global listener, listener_ready
        self.lease = None
        self.watchdog = None
        self.recent_ids = []
        self.closing = False
        self.accepted = False
        self.awaiting_ack = False
        self.presence_updated = 0.0
        self.correlation_id = uuid4().hex
        # ponytail: bound process fanout at 256 sockets; use queued fanout after load evidence.
        if len(subscribers) >= 256:
            await self.close(code=4429)
            return
        if self.scope.get("query_string") or (
            settings.AUTHENTICATION_REQUIRE_HTTPS and self.scope.get("scheme") != "wss"
        ):
            await self.close(code=4403)
            return
        try:
            current = await database_sync_to_async(audience)(self.scope)
            if current is None:
                await self.close(code=4401)
                return
            self.lease = await database_sync_to_async(acquire)(self.scope, current)
            if self.lease is None:
                await self.close(code=4429)
                return
            self.unit_id = current.unit_id
        except APIException:
            await self.close(code=4429)
            return
        except DatabaseError:
            await self.close(code=1013)
            return
        subscribers.add(self)
        if listener is None or listener.done():
            listener_ready = asyncio.Event()
            listener = asyncio.create_task(listen(listener_ready))
        ready = listener_ready
        if ready is None:
            await self.close(code=1013)
            return
        try:
            await asyncio.wait_for(ready.wait(), timeout=5)
        except TimeoutError:
            await self.close(code=1013)
            return
        if self.closing:
            return
        if listener is None or listener.done():
            await self.close(code=1013)
            return
        await self.accept()
        self.accepted = True
        # Current HTTP state recovers notifications committed before subscription.
        await self.refresh(None)
        self.watchdog = asyncio.create_task(self.watch())

    async def refresh(self, event):
        if self.closing or not self.accepted:
            return
        if event is not None and event.unit_id != self.unit_id:
            return
        current = await database_sync_to_async(audience)(self.scope)
        if current is None:
            await self.close(code=4401)
            return
        if event is not None:
            if not current.permits(event) or event.id in self.recent_ids:
                return
            self.recent_ids = (self.recent_ids + [event.id])[-100:]
        await asyncio.wait_for(
            self.send_json(
                {
                    "type": "refresh",
                    "event_id": str(event.id) if event else None,
                    "kind": event.kind if event else "SNAPSHOT_REQUIRED",
                }
            ),
            timeout=2,
        )

    async def watch(self):
        lease_id = self.lease
        if lease_id is None:
            await self.close(code=4401)
            return
        try:
            while True:
                await asyncio.sleep(5)
                current = await database_sync_to_async(audience)(self.scope)
                if (
                    current is None
                    or not await database_sync_to_async(
                        lambda: RealtimeLease.objects.filter(
                            id=lease_id, expires_at__gt=timezone.now()
                        ).exists()
                    )()
                ):
                    await self.close(code=4401)
                    return
                self.awaiting_ack = True
                await asyncio.wait_for(self.send_json({"type": "heartbeat"}), timeout=2)
        except (TimeoutError, psycopg.Error, DatabaseError, OSError):
            await self.close(code=1013)

    async def receive_json(self, content, **kwargs):
        # ASVS V4.4: only a solicited liveness acknowledgement is accepted.
        if content == {"type": "heartbeat_ack"} and self.awaiting_ack and self.accepted:
            self.awaiting_ack = False
            if not await database_sync_to_async(renew)(self.lease):
                await self.close(code=4401)
                return
            now = asyncio.get_running_loop().time()
            if self.scope["path"] == "/ws/v1/public/" and now - self.presence_updated >= 20:
                current = await database_sync_to_async(audience)(self.scope)
                if current is None:
                    await self.close(code=4401)
                    return
                await database_sync_to_async(
                    lambda: DeviceAccess.objects.filter(id=current.actor[2:]).update(
                        last_seen_at=timezone.now()
                    )
                )()
                self.presence_updated = now
            return
        await self.close(code=4400)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data is None or len(text_data) > 256:
            await self.close(code=4400)
            return
        try:
            content = json.loads(text_data)
        except ValueError:
            await self.close(code=4400)
            return
        await self.receive_json(content)

    async def close(self, code=None, reason=None):
        self.closing = True
        logger.info(
            "socket_closed",
            extra={
                "request_id": self.correlation_id,
                "endpoint": self.scope["path"],
                "close_code": code,
                "environment": settings.SETTINGS_MODULE.rsplit(".", 1)[-1],
            },
        )
        await super().close(code=code, reason=reason)

    async def disconnect(self, close_code):
        global listener, listener_ready
        subscribers.discard(self)
        logger.info(
            "socket_disconnected",
            extra={
                "request_id": self.correlation_id,
                "endpoint": self.scope["path"],
                "close_code": close_code,
            },
        )
        if self.watchdog:
            self.watchdog.cancel()
            with suppress(asyncio.CancelledError):
                await self.watchdog
        if self.lease:
            await database_sync_to_async(
                lambda: RealtimeLease.objects.filter(id=self.lease).delete()
            )()
        if not subscribers and listener and not listener.done():
            previous_listener = listener
            listener = None
            listener_ready = None
            previous_listener.cancel()
            with suppress(asyncio.CancelledError):
                await previous_listener

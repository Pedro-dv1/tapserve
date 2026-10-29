"""Point capabilities are scoped, encrypted at rest, bounded and revocable."""

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Cast, Concat
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.identity.models import AuditEvent
from apps.identity.permissions import require_permission
from apps.identity.services import rate_limit
from apps.organizations.models import Unit
from common.idempotency import Conflict, remember, replay
from common.network import client_address

from .models import DeviceAccess, ServicePoint


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def cipher() -> MultiFernet:
    return MultiFernet([Fernet(key) for key in settings.TAPSERVE_TOKEN_KEYS])


def point_url(point: ServicePoint) -> str:
    return (
        settings.PUBLIC_APP_ORIGIN
        + "/a/"
        + cipher().decrypt(bytes(point.token_ciphertext)).decode()
    )


def live_devices(unit):
    """Count distinct authenticated browsers with a live, acknowledged socket lease."""
    from apps.orders.models import RealtimeLease
    from apps.orders.services import OPEN_STATES

    devices = DeviceAccess.objects.filter(
        point__unit=unit,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
        point__active=True,
        point__unit__active=True,
        point__unit__company__active=True,
        point_token_version=F("point__token_version"),
        last_seen_at__gt=timezone.now() - timedelta(seconds=30),
    ).filter(Q(session__isnull=True) | Q(session__status__in=OPEN_STATES))
    return devices.annotate(actor=Concat(Value("D:"), Cast("id", CharField()))).filter(
        actor__in=RealtimeLease.objects.filter(
            unit=unit, expires_at__gt=timezone.now(), acknowledged=True
        ).values("actor")
    )


def connected_devices(point):
    from apps.orders.models import SessionPoint

    session_id = (
        SessionPoint.objects.filter(point=point, ended_at__isnull=True)
        .values_list("session_id", flat=True)
        .first()
    )
    return live_devices(point.unit).filter(
        **({"session_id": session_id} if session_id else {"point": point, "session": None})
    )


@transaction.atomic
def configure_identifier(identity, identifier, data):
    require_permission(identity, "MANAGE_SERVICE_POINTS")
    # ASVS V8: resource authorization stays at the server's unit boundary.
    point = (
        ServicePoint.objects.select_for_update()
        .filter(id=identifier, unit=identity.staff.unit)
        .first()
    )
    if point is None:
        raise NotFound()
    if point.token_version != data["expected_version"]:
        raise Conflict("O identificador mudou. Atualize o ponto antes de continuar.")
    if data["action"] == "ASSOCIATE":
        candidate = data.get("url", "")
        if urlsplit(candidate) != urlsplit(point_url(point)):
            raise ValidationError({"url": "Use o link atual deste ponto e do domínio configurado."})
    else:
        if not data["confirmed"]:
            raise ValidationError("Confirme a invalidação do link distribuído.")
        token = secrets.token_urlsafe(32)
        point.token_digest = digest(token)
        point.token_ciphertext = cipher().encrypt(token.encode())
        point.token_version += 1
        point.save(update_fields=["token_digest", "token_ciphertext", "token_version"])
        # Rotation invalidates the distributed URL, preserving existing device capabilities.
        DeviceAccess.objects.filter(point=point, revoked_at__isnull=True).update(
            point_token_version=point.token_version
        )
    AuditEvent.objects.create(
        unit=point.unit,
        staff=identity.staff,
        action="POINT_IDENTIFIER_" + data["action"],
        resource_id=str(point.id),
        reason=data["reason"],
    )
    return point


@transaction.atomic
def create_point(identity, data: dict):
    require_permission(identity, "MANAGE_SERVICE_POINTS")
    Unit.objects.select_for_update().get(id=identity.staff.unit_id)
    previous = replay(
        str(identity.staff.id),
        "CREATE_POINT",
        str(identity.staff.unit_id),
        data["idempotency_key"],
        data,
    )
    if previous:
        return previous.response
    from apps.catalog.models import Menu

    menu = None
    if "menu" in data:
        menu = Menu.objects.filter(id=data["menu"], unit=identity.staff.unit, active=True).first()
        if menu is None:
            raise ValidationError({"menu": "Selecione um cardápio ativo desta unidade."})
    else:
        candidates = list(
            Menu.objects.filter(unit=identity.staff.unit, active=True).order_by("id")[:2]
        )
        if len(candidates) == 1:
            menu = candidates[0]
        elif candidates:
            raise ValidationError({"menu": "Selecione o cardápio deste ponto."})
    token = secrets.token_urlsafe(32)
    try:
        with transaction.atomic():
            point = ServicePoint.objects.create(
                unit=identity.staff.unit,
                menu=menu,
                number=data.get("number"),
                name=data["name"],
                type=data["type"],
                nfc_enabled=data["nfc_enabled"],
                qr_enabled=data["qr_enabled"],
                token_digest=digest(token),
                token_ciphertext=cipher().encrypt(token.encode()),
            )
    except IntegrityError as error:
        raise ValidationError({"number": "Número já cadastrado nesta unidade."}) from error
    from .serializers import PointOutput

    response = dict(PointOutput(point).data)
    remember(
        identity.staff.unit,
        str(identity.staff.id),
        "CREATE_POINT",
        str(identity.staff.unit_id),
        data["idempotency_key"],
        data,
        response,
        201,
    )
    AuditEvent.objects.create(
        unit=point.unit, staff=identity.staff, action="POINT_CREATED", resource_id=str(point.id)
    )
    return response


def active_device(token: str | None):
    if not token or len(token) > 128:
        return None
    now = timezone.now()
    device = (
        DeviceAccess.objects.select_related("point__unit__company", "session")
        .filter(
            token_digest=digest(token),
            revoked_at__isnull=True,
            expires_at__gt=now,
            point__active=True,
            point__unit__active=True,
            point__unit__company__active=True,
        )
        .first()
    )
    if device is None or device.point_token_version != device.point.token_version:
        return None
    if device.session is not None and device.session.status not in {
        "OPEN",
        "CHECK_REQUESTED",
        "CLOSING",
        "REOPENED",
    }:
        return None
    return device


def exchange(request, token: str):
    rate_limit("access-ip:" + client_address(request), 30)
    rate_limit("access-point:" + digest(token), 30)
    browser = request.session.get("tapserve_browser_nonce")
    if not isinstance(browser, str):
        raise PermissionDenied("Atualize a página.")
    with transaction.atomic():
        point = (
            ServicePoint.objects.select_for_update(of=("self",))
            .select_related("unit__company")
            .filter(
                token_digest=digest(token),
                active=True,
                access_enabled=True,
                unit__active=True,
                unit__company__active=True,
            )
            .first()
        )
        if point is None:
            raise NotFound()
        if not point.qr_enabled and not point.nfc_enabled:
            raise NotFound()
        from apps.orders.models import ServiceSession, SessionPoint
        from apps.orders.services import OPEN_STATES

        link = SessionPoint.objects.filter(point=point, ended_at__isnull=True).first()
        session = (
            ServiceSession.objects.select_for_update().get(id=link.session_id) if link else None
        )
        if session is not None and session.status not in OPEN_STATES:
            raise Conflict()
        existing = active_device(request.COOKIES.get(settings.DEVICE_COOKIE_NAME))
        if existing is not None and existing.point_id != point.id:
            raise Conflict()
        recovered = (
            DeviceAccess.objects.filter(
                point=point,
                browser_digest=digest(browser),
                point_token_version=point.token_version,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .filter(Q(session__isnull=True) | Q(session__status__in=OPEN_STATES))
            .first()
        )
        device = existing if existing is not None else recovered
        if device is not None:
            if device.session_id is not None and (
                session is None or device.session_id != session.id
            ):
                raise Conflict()
            if device.session_id is None and session is not None:
                device.session = session
                device.save(update_fields=["session"])
            return device, cipher().decrypt(bytes(device.token_ciphertext)).decode()
        if point.block_new_devices:
            raise PermissionDenied()
        authorized = DeviceAccess.objects.filter(
            **({"session": session} if session is not None else {"point": point}),
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            point_token_version=F("point__token_version"),
        ).filter(Q(session__isnull=True) | Q(session__status__in=OPEN_STATES))
        if authorized.count() >= 5:
            from apps.orders.models import RealtimeLease

            cutoff = timezone.now() - timedelta(minutes=5)
            # Idle authorizations release slots only when needed; live sockets keep their access.
            reclaimed = (
                authorized.annotate(actor=Concat(Value("D:"), Cast("id", CharField())))
                .filter(issued_at__lte=cutoff)
                .filter(Q(last_seen_at__isnull=True) | Q(last_seen_at__lte=cutoff))
                .exclude(
                    actor__in=RealtimeLease.objects.filter(
                        unit_id=point.unit_id, expires_at__gt=timezone.now()
                    ).values("actor")
                )
                .update(revoked_at=timezone.now())
            )
            if reclaimed:
                AuditEvent.objects.create(
                    unit=point.unit,
                    action="DEVICE_IDLE_EXPIRED",
                    resource_id=str(point.id),
                    details={"count": reclaimed},
                )
        if authorized.count() >= 5:
            raise Conflict("Limite de dispositivos atingido.")
        capability = secrets.token_urlsafe(32)
        device = DeviceAccess.objects.create(
            point=point,
            session=session,
            token_digest=digest(capability),
            token_ciphertext=cipher().encrypt(capability.encode()),
            browser_digest=digest(browser),
            point_token_version=point.token_version,
            expires_at=timezone.now() + timedelta(hours=12),
        )
        AuditEvent.objects.create(
            unit=point.unit, action="DEVICE_AUTHORIZED", resource_id=str(device.id)
        )
        return device, capability


@transaction.atomic
def change_point(identity, identifier, data):
    require_permission(identity, "MANAGE_SERVICE_POINTS")
    point = (
        ServicePoint.objects.select_for_update()
        .filter(id=identifier, unit=identity.staff.unit)
        .first()
    )
    if point is None:
        raise NotFound()
    if "menu" in data and data["menu"] != point.menu_id:
        from apps.catalog.models import Menu
        from apps.orders.models import SessionPoint

        if SessionPoint.objects.filter(point=point, ended_at__isnull=True).exists():
            raise Conflict("Finalize o atendimento antes de trocar o cardápio do ponto.")
        menu = Menu.objects.filter(id=data["menu"], unit=point.unit, active=True).first()
        if menu is None:
            raise ValidationError({"menu": "Selecione um cardápio ativo desta unidade."})
        data = {**data, "menu": menu}
        DeviceAccess.objects.filter(point=point, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
    elif "menu" in data:
        data = {**data, "menu": point.menu}
    before = {"number": point.number, "name": point.name}
    fields = (
        "number",
        "name",
        "active",
        "access_enabled",
        "nfc_enabled",
        "qr_enabled",
        "block_new_devices",
        "menu",
    )
    for key in fields:
        if key in data:
            setattr(point, key, data[key])
    try:
        with transaction.atomic():
            point.save(update_fields=[key for key in fields if key in data])
    except IntegrityError as error:
        raise ValidationError({"number": "Número já cadastrado nesta unidade."}) from error
    if not point.active:
        DeviceAccess.objects.filter(point=point, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
    AuditEvent.objects.create(
        unit=point.unit,
        staff=identity.staff,
        action="POINT_UPDATED",
        resource_id=str(point.id),
        reason=data["reason"],
        details={"before": before, "after": {"number": point.number, "name": point.name}},
    )
    from apps.orders.production import publish

    publish(None, "POINT_UPDATED", [], point=point)
    return point


@transaction.atomic
def revoke_device(identity, identifier, reason):
    require_permission(identity, "MANAGE_SERVICE_POINTS")
    candidate = DeviceAccess.objects.filter(id=identifier, point__unit=identity.staff.unit).first()
    if candidate is None:
        raise NotFound()
    ServicePoint.objects.select_for_update().get(id=candidate.point_id)
    DeviceAccess.objects.filter(id=identifier, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
    AuditEvent.objects.create(
        unit=identity.staff.unit,
        staff=identity.staff,
        action="DEVICE_REVOKED",
        resource_id=str(identifier),
        reason=reason,
    )

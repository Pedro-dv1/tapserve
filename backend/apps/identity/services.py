"""Authoritative identity flows; PINs never leave hash storage or input handling."""

import hashlib
import secrets
import time
from datetime import UTC, datetime

from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
    Throttled,
    ValidationError,
)

from apps.organizations.models import Unit
from common.idempotency import remember, replay
from common.network import client_address, require_pin_network

from .authentication import StaffIdentity
from .models import AuditEvent, Permission, Role, Staff
from .permissions import PERMISSION_CODES, ROLE_DEFAULTS

DUMMY_PIN_HASH = make_password(secrets.token_urlsafe(32), hasher="argon2")


def rate_limit(key: str, limit: int, window_seconds: int = 300) -> None:
    """PG UPSERT increments atomically across processes; persist failed attempts too."""
    digest = hashlib.sha256(key.encode()).hexdigest()
    window = int(time.time()) // window_seconds
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO identity_ratebucket (key, "window", attempts, expires_at) VALUES (%s, %s, 1, %s) '
            'ON CONFLICT (key) DO UPDATE SET "window" = EXCLUDED."window", '
            'attempts = CASE WHEN identity_ratebucket."window" = EXCLUDED."window" '
            "THEN LEAST(identity_ratebucket.attempts + 1, %s) ELSE 1 END, expires_at=EXCLUDED.expires_at RETURNING attempts",
            [
                digest,
                window,
                datetime.fromtimestamp((window + 1) * window_seconds, tz=UTC),
                limit + 1,
            ],
        )
        attempts = cursor.fetchone()[0]
    if attempts > limit:
        raise Throttled(wait=window_seconds - int(time.time()) % window_seconds)


def authenticate_staff(request, data: dict[str, str], strong: bool) -> Staff:
    rate_limit("staff-ip:" + client_address(request), 30)
    if not strong:
        require_pin_network(request)
    identifier = data["username"] if strong else data["login_code"]
    rate_limit(f"staff-identity:{data['company']}:{data['unit']}:{identifier}", 5)
    scope = {
        "unit__company__slug": data["company"],
        "unit__slug": data["unit"],
        "active": True,
        "unit__active": True,
        "unit__company__active": True,
    }
    if strong:
        user = authenticate(request=request, username=data["username"], password=data["password"])
        staff = (
            Staff.objects.select_related("unit", "role").filter(user=user, **scope).first()
            if user is not None
            else None
        )
        valid = staff is not None
    else:
        staff = (
            Staff.objects.select_related("unit", "role")
            .filter(login_code=data["login_code"], **scope)
            .exclude(user__is_active=False)
            .first()
        )
        valid = check_password(data["pin"], staff.pin_hash if staff is not None else DUMMY_PIN_HASH)
        valid = valid and staff is not None and staff.role.name not in {"OWNER", "ADMIN"}
    if not valid or staff is None:
        if staff is not None:
            AuditEvent.objects.create(unit=staff.unit, staff=staff, action="STAFF_LOGIN_FAILED")
        raise AuthenticationFailed("Credenciais inválidas.")
    if strong:
        request.session.flush()
        login(request, user)
    else:
        # Remove any prior Django identity; cycle the opaque session to prevent fixation.
        request.session.flush()
        request.session.cycle_key()
    request.session.update(
        {
            "tapserve_staff_id": str(staff.id),
            "tapserve_credential_version": staff.credential_version,
            "tapserve_auth_strength": "password" if strong else "pin",
            "tapserve_issued_at": int(time.time()),
            "tapserve_seen_at": int(time.time()),
        }
    )
    request.session.set_expiry(28800)
    AuditEvent.objects.create(unit=staff.unit, staff=staff, action="STAFF_LOGIN")
    return staff


@transaction.atomic
def initialize_roles(unit: Unit) -> None:
    for code in PERMISSION_CODES:
        Permission.objects.get_or_create(code=code)
    for name, codes in ROLE_DEFAULTS.items():
        role, created = Role.objects.get_or_create(unit=unit, name=name)
        if created:
            role.suggested_permissions.set(Permission.objects.filter(code__in=codes))


def checked_grants(actor: StaffIdentity, codes: list[str]) -> list[Permission]:
    # ponytail: serialize rare staff administration per unit; use ordered staff locks if measured contention warrants it.
    unit = (
        Unit.objects.select_for_update()
        .filter(id=actor.staff.unit_id, active=True, company__active=True)
        .first()
    )
    current = Staff.objects.filter(
        id=actor.staff.id, unit=unit, active=True, credential_version=actor.staff.credential_version
    ).first()
    current_permissions = (
        frozenset(current.permissions.values_list("code", flat=True))
        if current is not None
        else frozenset()
    )
    if (
        not actor.strong
        or "MANAGE_STAFF" not in current_permissions
        or not set(codes).issubset(current_permissions)
    ):
        raise PermissionDenied()
    if not set(codes).issubset(PERMISSION_CODES):
        raise ValidationError("Permissão inválida.")
    return list(Permission.objects.filter(code__in=codes))


@transaction.atomic
def create_staff(actor: StaffIdentity, data: dict) -> Staff:
    role = Role.objects.filter(id=data["role_id"], unit=actor.staff.unit).first()
    if role is None or role.name in {"OWNER", "ADMIN"}:
        # Elevated account binding is performed through the strong, interactive setup command.
        raise ValidationError("Perfil não permitido nesta operação.")
    grants = checked_grants(actor, data["permissions"])
    key = data.get("idempotency_key")
    # ASVS V14: a short PIN must not leave a brute-forceable, unkeyed persisted digest.
    body = {**data, "pin": salted_hmac("staff-create-pin", data["pin"]).hexdigest()}
    if key:
        previous = replay(str(actor.staff.id), "CREATE_STAFF", str(actor.staff.unit_id), key, body)
        if previous:
            return Staff.objects.get(id=previous.response["id"], unit=actor.staff.unit)
    try:
        with transaction.atomic():
            staff = Staff.objects.create(
                unit=actor.staff.unit,
                role=role,
                name=data["name"],
                login_code=data["login_code"],
                pin_hash=make_password(data["pin"], hasher="argon2"),
            )
            staff.permissions.set(grants)
    except IntegrityError as error:
        raise ValidationError("Código já cadastrado.") from error
    AuditEvent.objects.create(
        unit=actor.staff.unit, staff=actor.staff, action="STAFF_CREATED", resource_id=str(staff.id)
    )
    if key:
        remember(
            actor.staff.unit,
            str(actor.staff.id),
            "CREATE_STAFF",
            str(actor.staff.unit_id),
            key,
            body,
            {"id": str(staff.id)},
            201,
        )
    return staff


@transaction.atomic
def update_staff(actor: StaffIdentity, identifier, data: dict) -> Staff:
    granted = checked_grants(actor, data.get("permissions", []))
    grants = granted if "permissions" in data else None
    staff = (
        Staff.objects.select_for_update()
        .filter(id=identifier, unit=actor.staff.unit, deleted_at__isnull=True)
        .first()
    )
    if staff is None:
        from rest_framework.exceptions import NotFound

        raise NotFound()
    if staff.id == actor.staff.id or staff.role.name in {"OWNER", "ADMIN"}:
        raise PermissionDenied()
    if "name" in data:
        staff.name = data["name"]
    if "active" in data:
        staff.active = data["active"]
    if "pin" in data:
        staff.pin_hash = make_password(data["pin"], hasher="argon2")
    staff.credential_version += 1
    staff.save()
    if grants is not None:
        staff.permissions.set(grants)
    AuditEvent.objects.create(
        unit=actor.staff.unit,
        staff=actor.staff,
        action="STAFF_PIN_RESET" if "pin" in data else "STAFF_UPDATED",
        resource_id=str(staff.id),
        reason=data["reason"],
    )
    return staff


@transaction.atomic
def delete_staff(actor: StaffIdentity, identifier, reason=""):
    # ASVS V8: authorize and retain referenced identities for operational/financial history.
    checked_grants(actor, [])
    staff = Staff.objects.select_for_update().filter(id=identifier, unit=actor.staff.unit).first()
    if staff is None:
        from rest_framework.exceptions import NotFound

        raise NotFound()
    if staff.id == actor.staff.id or staff.role.name in {"OWNER", "ADMIN"}:
        raise PermissionDenied()
    if staff.deleted_at is not None:
        return
    staff.active = False
    staff.deleted_at = timezone.now()
    staff.credential_version += 1
    staff.save(update_fields=["active", "deleted_at", "credential_version"])
    AuditEvent.objects.create(
        unit=actor.staff.unit,
        staff=actor.staff,
        action="STAFF_DELETED",
        resource_id=str(staff.id),
        reason=reason,
    )

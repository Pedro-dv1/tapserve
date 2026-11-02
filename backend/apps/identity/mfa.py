"""TOTP via cryptography; partial login never creates an authenticated identity."""

import hashlib
import re
import secrets
import time
from datetime import timedelta

from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.twofactor import InvalidToken
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.api import CookieMutationAPIView
from common.network import client_address

from .models import (
    AuditEvent,
    MfaChallenge,
    MfaCredential,
    PlatformAuditEvent,
    PlatformOperator,
    Staff,
)
from .permissions import ELEVATED_PERMISSIONS, MANAGEMENT_ROLES, IsActiveStaff
from .serializers import StrictSerializer
from .services import complete_staff_login, rate_limit


def totp(secret):
    # RFC 6238 HMAC-SHA1 interoperability; no collision-sensitive SHA1 digest is used.
    return TOTP(secret, 6, SHA1(), 30)  # noqa: S303


def token_cipher():
    from apps.access.services import cipher

    return cipher()


def requires_mfa(staff):
    return staff.user_id is not None and (
        staff.role.name in {"OWNER", "ADMIN"}
        or staff.role.name in MANAGEMENT_ROLES
        and staff.permissions.filter(code__in=ELEVATED_PERMISSIONS).exists()
        or MfaCredential.objects.filter(user_id=staff.user_id, confirmed_at__isnull=False).exists()
    )


def session_verified(session, user, *, staff=None):
    if staff is not None and not requires_mfa(staff):
        return True
    return MfaCredential.objects.filter(
        user=user,
        confirmed_at__isnull=False,
        version=session.get("tapserve_mfa_version"),
    ).exists()


def audit(user, action, *, staff=None, reason=""):
    if staff is not None:
        AuditEvent.objects.create(
            unit=staff.unit, staff=staff, action=action, resource_id=str(user.pk), reason=reason
        )
    else:
        operator = PlatformOperator.objects.filter(user=user).first()
        if operator is not None:
            PlatformAuditEvent.objects.create(
                operator=operator, action=action, resource_id=str(user.pk)
            )


def challenge_data(challenge):
    data = {"mfa_required": True, "enrollment_required": bool(challenge.secret_ciphertext),
            "expires_at": challenge.expires_at}
    if challenge.secret_ciphertext:
        # ASVS V6.5: enrollment material is returned only after password verification.
        secret = token_cipher().decrypt(bytes(challenge.secret_ciphertext))
        data["provisioning_uri"] = totp(secret).get_provisioning_uri(
            challenge.user.get_username(), "TapServe"
        )
    return data


def begin_challenge(request, user, realm, *, staff=None, replacing=False):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        credential, _ = MfaCredential.objects.get_or_create(user=user)
        seed = token_cipher().encrypt(secrets.token_bytes(20)) if (
            credential.confirmed_at is None or replacing
        ) else b""
        challenge = MfaChallenge.objects.create(
            user=user, staff=staff, realm=realm, secret_ciphertext=seed,
            credential_version=credential.version,
            staff_version=staff.credential_version if staff is not None else None,
            password_digest=user.get_session_auth_hash(), replacing=replacing,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        audit(user, "MFA_CHALLENGE", staff=staff)
    # Partial credentials replace any previous authenticated browser identity.
    request.session.flush()
    request.session["tapserve_mfa_challenge"] = str(challenge.id)
    request.session.set_expiry(300)
    return challenge_data(challenge)


def verify_totp(credential, code, *, secret=None):
    if not re.fullmatch(r"[0-9]{6}", code):
        return False
    otp = totp(secret or token_cipher().decrypt(bytes(credential.secret_ciphertext)))
    current = int(time.time()) // 30
    for counter in (current, current - 1, current + 1):
        if counter < 0 or counter <= credential.last_counter:
            continue
        try:
            otp.verify(code.encode("ascii"), counter * 30)
        except InvalidToken:
            continue
        credential.last_counter = counter
        return True
    return False


def verify_factor(credential, code):
    if verify_totp(credential, code):
        return "TOTP"
    digest = hashlib.sha256(code.encode()).hexdigest()
    hashes = list(credential.recovery_hashes)
    matched = next((value for value in hashes if secrets.compare_digest(value, digest)), None)
    if matched is None:
        raise AuthenticationFailed("Código inválido ou já utilizado.")
    credential.recovery_hashes = [value for value in hashes if value != matched]
    return "RECOVERY"


def finish_challenge(request, code, realm):
    rate_limit("mfa-ip:" + client_address(request), 30)
    candidate = MfaChallenge.objects.filter(
        id=request.session.get("tapserve_mfa_challenge"), realm=realm
    ).first()
    if candidate is None:
        raise AuthenticationFailed("Reinicie o login para obter um desafio válido.")
    # Counters commit even when verification fails or the transaction rolls back.
    rate_limit("mfa-user:" + str(candidate.user_id), 5)
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=candidate.user_id)
        challenge = MfaChallenge.objects.select_for_update().get(pk=candidate.pk)
        credential = MfaCredential.objects.select_for_update().get(user=user)
        if (
            not user.is_active or challenge.used_at is not None
            or challenge.expires_at <= timezone.now()
            or credential.version != challenge.credential_version
            or not secrets.compare_digest(challenge.password_digest, user.get_session_auth_hash())
        ):
            raise AuthenticationFailed("Reinicie o login para obter um desafio válido.")
        staff = None
        if realm == "STAFF":
            if challenge.staff_id is None or challenge.staff_version is None:
                raise AuthenticationFailed()
            staff = Staff.objects.select_related("unit__company", "role", "user").filter(
                id=challenge.staff_id, user=user, active=True, unit__active=True,
                unit__company__active=True, credential_version=challenge.staff_version,
            ).first()
            if staff is None:
                raise AuthenticationFailed()
        elif not PlatformOperator.objects.filter(user=user, active=True).exists():
            raise AuthenticationFailed()
        recovery_codes = []
        if challenge.secret_ciphertext:
            credential.last_counter = -1
            secret = token_cipher().decrypt(bytes(challenge.secret_ciphertext))
            if not verify_totp(credential, code, secret=secret):
                raise AuthenticationFailed("Código inválido.")
            credential.secret_ciphertext = challenge.secret_ciphertext
            credential.confirmed_at = timezone.now()
            credential.version += 1
            recovery_codes = [secrets.token_hex(16) for _ in range(10)]
            credential.recovery_hashes = [
                hashlib.sha256(value.encode()).hexdigest() for value in recovery_codes
            ]
            audit(user, "MFA_REPLACED" if challenge.replacing else "MFA_ENROLLED", staff=staff)
        else:
            if credential.confirmed_at is None:
                raise AuthenticationFailed()
            method = verify_factor(credential, code)
            audit(user, "MFA_RECOVERY_USED" if method == "RECOVERY" else "MFA_VERIFIED", staff=staff)
        credential.save()
        challenge.used_at = timezone.now()
        challenge.secret_ciphertext = b""
        challenge.save(update_fields=["used_at", "secret_ciphertext"])
        if staff is not None:
            complete_staff_login(request, staff, strong=True, mfa_version=credential.version)
            from .views import context_data

            result = context_data(staff, True)
        else:
            request.session.flush()
            login(request, user)
            request.session.update({
                "tapserve_platform": True, "tapserve_mfa_version": credential.version,
                "platform_issued_at": int(time.time()), "platform_seen_at": int(time.time()),
            })
            request.session.set_expiry(28800)
            audit(user, "PLATFORM_LOGIN")
            result = {"username": user.get_username()}
        if recovery_codes:
            # Returned only once, never stored in plaintext or included in audit details.
            result["recovery_codes"] = recovery_codes
        return result


class MfaCodeInput(StrictSerializer):
    code = serializers.RegexField(r"^(?:[0-9]{6}|[a-f0-9]{32})$", write_only=True)


class MfaChangeInput(MfaCodeInput):
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class MfaChallengeOutput(serializers.Serializer):
    mfa_required = serializers.BooleanField()
    enrollment_required = serializers.BooleanField()
    expires_at = serializers.DateTimeField()
    provisioning_uri = serializers.CharField(required=False)


class StaffMfaChallengeView(CookieMutationAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    realm = "STAFF"

    @extend_schema(request=MfaCodeInput, responses=dict, auth=[])
    def post(self, request):
        if settings.AUTHENTICATION_REQUIRE_HTTPS and not request.is_secure():
            raise PermissionDenied()
        data = MfaCodeInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            result = finish_challenge(request._request, data.validated_data["code"], self.realm)
        except AuthenticationFailed:
            candidate = MfaChallenge.objects.select_related("user", "staff__unit").filter(
                id=request.session.get("tapserve_mfa_challenge"), realm=self.realm
            ).first()
            if candidate is not None:
                audit(candidate.user, "MFA_FAILED", staff=candidate.staff)
            raise
        return Response(result)


class PlatformMfaChallengeView(StaffMfaChallengeView):
    realm = "PLATFORM"


def change_credential(request, *, realm, remove=False):
    data = MfaChangeInput(data=request.data)
    data.is_valid(raise_exception=True)
    user = request._request.user
    rate_limit("mfa-change:" + str(user.pk), 5)
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=user.pk)
        credential = MfaCredential.objects.select_for_update().filter(
            user=user, confirmed_at__isnull=False
        ).first()
        if credential is None:
            raise PermissionDenied()
        if not user.check_password(data.validated_data["password"]):
            raise AuthenticationFailed()
        method = verify_factor(credential, data.validated_data["code"])
        credential.save(update_fields=["last_counter", "recovery_hashes"])
        staff = request.auth.staff if realm == "STAFF" else None
        if method == "RECOVERY":
            audit(user, "MFA_RECOVERY_USED", staff=staff)
        if not remove:
            return begin_challenge(request._request, user, realm, staff=staff, replacing=True)
        credential.confirmed_at = None
        credential.secret_ciphertext = b""
        credential.recovery_hashes = []
        credential.last_counter = -1
        credential.version += 1
        credential.save()
        Staff.objects.filter(user=user).update(credential_version=F("credential_version") + 1)
        MfaChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        audit(user, "MFA_RESET", staff=staff)
        request.session.flush()
        return {"enrollment_required": True}


class StaffMfaSettingsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]
    realm = "STAFF"

    def check_strong(self, request):
        if not request.auth.strong or not session_verified(
            request.session, request._request.user, staff=request.auth.staff
        ):
            raise PermissionDenied()

    @extend_schema(responses=dict)
    def get(self, request):
        self.check_strong(request)
        factor = MfaCredential.objects.filter(user=request._request.user).first()
        return Response({"enabled": bool(factor and factor.confirmed_at),
                         "recovery_codes_remaining": len(factor.recovery_hashes) if factor else 0})

    @extend_schema(request=MfaChangeInput, responses=MfaChallengeOutput)
    def post(self, request):
        self.check_strong(request)
        return Response(change_credential(request, realm=self.realm))

    @extend_schema(request=MfaChangeInput, responses=dict)
    def delete(self, request):
        self.check_strong(request)
        return Response(change_credential(request, realm=self.realm, remove=True))


# Imported after challenge functions: platform login imports begin_challenge at runtime.
from .platform import IsPlatformOperator, PlatformAuthentication  # noqa: E402


class PlatformMfaSettingsView(StaffMfaSettingsView):
    authentication_classes = [PlatformAuthentication]
    permission_classes = [IsPlatformOperator]
    realm = "PLATFORM"

    def check_strong(self, request):
        if not session_verified(request.session, request._request.user):
            raise PermissionDenied()

"""Staff consent bound to a server-side browser nonce, never to a claimed location."""

from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.identity.models import AuditEvent
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from apps.identity.services import rate_limit
from common.api import CookieMutationAPIView, page_serializer
from common.idempotency import Conflict, remember, replay

from .models import DeviceAccess, DeviceAdmission, ServicePoint
from .serializers import ReasonInput


def invalidate_admissions(point_ids, session_id=None):
    admissions = DeviceAdmission.objects.filter(
        point_id__in=point_ids, status__in=["PENDING", "APPROVED"]
    )
    if session_id is not None:
        admissions = admissions.filter(Q(session_id=session_id) | Q(session__isnull=True))
    return admissions.update(status="REVOKED")


def admission_for(point, browser_digest, session):
    """Caller holds point then session locks, matching exchange/close."""
    now = timezone.now()
    DeviceAdmission.objects.filter(
        point=point, device__isnull=True, expires_at__lte=now, status__in=["PENDING", "APPROVED"]
    ).update(status="EXPIRED")
    admission = (
        DeviceAdmission.objects.filter(point=point, browser_digest=browser_digest)
        .order_by("-requested_at")
        .first()
    )
    if (
        admission
        and admission.point_token_version == point.token_version
        and admission.expires_at > now
    ):
        if admission.status == "REJECTED":
            raise PermissionDenied("A solicitação foi recusada ou revogada. Peça ajuda à equipe.")
        if admission.status in {"PENDING", "APPROVED"}:
            if admission.session_id is None or admission.session_id == getattr(session, "id", None):
                return admission
    DeviceAdmission.objects.filter(
        point=point, browser_digest=browser_digest, status__in=["PENDING", "APPROVED"]
    ).update(status="REVOKED")
    if (
        DeviceAdmission.objects.filter(point=point, status="PENDING", expires_at__gt=now).count()
        >= 20
    ):
        raise Conflict("Há muitas solicitações pendentes. Peça ajuda à equipe.")
    admission = DeviceAdmission.objects.create(
        point=point,
        session=session,
        browser_digest=browser_digest,
        point_token_version=point.token_version,
        expires_at=now + timedelta(minutes=10),
    )
    from apps.orders.production import publish

    publish(session, "ADMISSION_PENDING", [], point=point)
    return admission


def admission_data(admission):
    # ASVS V8: pending browsers see only their own status, never a table's history.
    return {
        "admission_id": str(admission.id),
        "status": admission.status,
        "expires_at": admission.expires_at.isoformat(),
        "verification_code": str(admission.id).split("-")[0].upper(),
    }


class AdmissionOutput(serializers.ModelSerializer):
    point_name = serializers.CharField(source="point.label", read_only=True)
    verification_code = serializers.SerializerMethodField()

    def get_verification_code(self, obj) -> str:
        return str(obj.id).split("-")[0].upper()

    class Meta:
        model = DeviceAdmission
        fields = [
            "id",
            "point_id",
            "point_name",
            "status",
            "requested_at",
            "expires_at",
            "verification_code",
        ]


class AdmissionDecision(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])


class AdmissionQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    point = serializers.UUIDField(required=False)


class AdmissionPollView(CookieMutationAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=dict, auth=[])
    def get(self, request, identifier):
        from .services import browser_nonce, digest

        nonce = browser_nonce(request)
        if not isinstance(nonce, str):
            raise NotFound()
        rate_limit("admission-poll:" + digest(nonce), 30, 60)
        admission = DeviceAdmission.objects.filter(
            id=identifier, browser_digest=digest(nonce)
        ).first()
        if admission is None:
            raise NotFound()
        if admission.expires_at <= timezone.now() and admission.device_id is None:
            return Response({**admission_data(admission), "status": "EXPIRED"})
        return Response(admission_data(admission))


class AdmissionClaimView(CookieMutationAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=StrictSerializer, responses=dict, auth=[])
    def post(self, request, identifier):
        from django.conf import settings

        from .services import browser_nonce, cipher, digest, exchange
        from .views import device_response

        data = StrictSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if settings.AUTHENTICATION_REQUIRE_HTTPS and not request.is_secure():
            raise PermissionDenied()
        nonce = browser_nonce(request)
        if not isinstance(nonce, str):
            raise NotFound()
        admission = (
            DeviceAdmission.objects.select_related("point")
            .filter(
                id=identifier,
                browser_digest=digest(nonce),
                status="APPROVED",
                expires_at__gt=timezone.now(),
                point_token_version=F("point__token_version"),
            )
            .first()
        )
        if admission is None:
            raise NotFound()
        device, token = exchange(
            request._request, cipher().decrypt(bytes(admission.point.token_ciphertext)).decode()
        )
        if not isinstance(device, DeviceAccess):
            raise Conflict()
        return device_response(device, token)


class StaffAdmissionsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=page_serializer(AdmissionOutput))
    def get(self, request):
        require_permission(request.auth, "APPROVE_DEVICE_ACCESS")
        require_permission(request.auth, "VIEW_OPERATION")
        rows = (
            DeviceAdmission.objects.filter(
                point__unit=request.auth.staff.unit,
                point__active=True,
                status="PENDING",
                expires_at__gt=timezone.now(),
                point_token_version=F("point__token_version"),
            )
            .select_related("point")
            .order_by("requested_at", "id")
        )
        query = AdmissionQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        if "point" in query.validated_data:
            rows = rows.filter(point_id=query.validated_data["point"])
        pager = PageNumberPagination()
        return pager.get_paginated_response(
            AdmissionOutput(pager.paginate_queryset(rows, request), many=True).data
        )


def decide_admission(identity, identifier, data):
    rate_limit("admission-decision:" + str(identity.staff.id), 60, 60)
    return _decide_admission(identity, identifier, data)


@transaction.atomic
def _decide_admission(identity, identifier, data):
    require_permission(identity, "VIEW_OPERATION")
    require_permission(identity, "APPROVE_DEVICE_ACCESS")
    candidate = DeviceAdmission.objects.filter(
        id=identifier, point__unit=identity.staff.unit
    ).first()
    if candidate is None:
        raise NotFound()
    point = ServicePoint.objects.select_for_update().get(
        id=candidate.point_id, unit=identity.staff.unit
    )
    from apps.orders.models import ServiceSession, SessionPoint
    from apps.orders.services import OPEN_STATES

    link = SessionPoint.objects.filter(point=point, ended_at__isnull=True).first()
    session = ServiceSession.objects.select_for_update().get(id=link.session_id) if link else None
    admission = DeviceAdmission.objects.select_for_update().get(id=identifier)
    previous = replay(
        str(identity.staff.id),
        "ADMISSION_DECISION",
        str(admission.id),
        data["idempotency_key"],
        data,
    )
    if previous:
        return previous.response
    if (
        not point.active
        or not point.access_enabled
        or not point.unit.active
        or not point.unit.company.active
        or point.block_new_devices
        or admission.status != "PENDING"
        or admission.expires_at <= timezone.now()
        or admission.point_token_version != point.token_version
        or (session is not None and session.status not in OPEN_STATES)
        or (
            admission.session_id is not None
            and admission.session_id != getattr(session, "id", None)
        )
    ):
        raise Conflict("Esta solicitação expirou ou o atendimento mudou.")
    if data["status"] == "APPROVED":
        scope = {"session": session} if session else {"point": point, "session__isnull": True}
        devices = DeviceAccess.objects.filter(
            **scope,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            point_token_version=F("point__token_version"),
        ).count()
        if devices >= 5:
            from .services import reclaim_idle_devices

            reclaim_idle_devices(point, session)
            devices = DeviceAccess.objects.filter(
                **scope,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
                point_token_version=F("point__token_version"),
            ).count()
        reservations = DeviceAdmission.objects.filter(
            **scope, status="APPROVED", device__isnull=True, expires_at__gt=timezone.now()
        ).count()
        if devices + reservations >= 5:
            raise Conflict("Limite de dispositivos atingido.")
    admission.status = data["status"]
    admission.session = session
    admission.decided_at = timezone.now()
    admission.decided_by = identity.staff
    admission.save(update_fields=["status", "session", "decided_at", "decided_by"])
    AuditEvent.objects.create(
        unit=point.unit,
        staff=identity.staff,
        action="ADMISSION_" + admission.status,
        resource_id=str(admission.id),
    )
    from apps.orders.production import publish

    publish(session, "ADMISSION_CHANGED", [], point=point)
    result = admission_data(admission)
    remember(
        point.unit,
        str(identity.staff.id),
        "ADMISSION_DECISION",
        str(admission.id),
        data["idempotency_key"],
        data,
        result,
        200,
    )
    return result


class AdmissionDecisionView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=AdmissionDecision, responses=dict)
    def post(self, request, identifier):
        data = AdmissionDecision(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(decide_admission(request.auth, identifier, data.validated_data))


class RevokePointDevicesView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=ReasonInput, responses={204: None})
    @transaction.atomic
    def post(self, request, identifier):
        require_permission(request.auth, "MANAGE_SERVICE_POINTS")
        data = ReasonInput(data=request.data)
        data.is_valid(raise_exception=True)
        point = (
            ServicePoint.objects.select_for_update()
            .filter(id=identifier, unit=request.auth.staff.unit)
            .first()
        )
        if point is None:
            raise NotFound()
        DeviceAccess.objects.filter(point=point, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
        invalidate_admissions([point.id])
        AuditEvent.objects.create(
            unit=point.unit,
            staff=request.auth.staff,
            action="POINT_DEVICES_REVOKED",
            resource_id=str(point.id),
            reason=data.validated_data["reason"],
        )
        from apps.orders.production import publish

        publish(None, "ACCESS_REVOKED", [], point=point)
        return Response(status=204)


class NfcActionInput(StrictSerializer):
    action = serializers.ChoiceField(choices=["WRITE", "LOCK"])
    expected_version = serializers.IntegerField(min_value=1)


class NfcAuthorizeView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=NfcActionInput, responses=dict)
    @transaction.atomic
    def post(self, request, identifier):
        data = NfcActionInput(data=request.data)
        data.is_valid(raise_exception=True)
        require_permission(request.auth, "MANAGE_SERVICE_POINTS")
        require_permission(request.auth, "PROVISION_NFC")
        if data.validated_data["action"] == "LOCK":
            require_permission(request.auth, "LOCK_NFC_TAG")
        rate_limit("nfc-staff:" + str(request.auth.staff.id), 20, 60)
        point = (
            ServicePoint.objects.select_for_update()
            .filter(id=identifier, unit=request.auth.staff.unit)
            .first()
        )
        if point is None:
            raise NotFound()
        if (
            point.token_version != data.validated_data["expected_version"]
            or not point.active
            or not point.access_enabled
            or not point.nfc_enabled
        ):
            raise Conflict("O identificador mudou ou não está disponível para gravação.")
        AuditEvent.objects.create(
            unit=point.unit,
            staff=request.auth.staff,
            action="NFC_" + data.validated_data["action"] + "_AUTHORIZED",
            resource_id=str(point.id),
        )
        from .services import point_url

        return Response({"url": point_url(point), "token_version": point.token_version})

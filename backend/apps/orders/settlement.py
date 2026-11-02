"""Declared external receipts and the locked lifecycle of a consumption session."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.access.models import DeviceAccess, ServicePoint
from apps.identity.models import AuditEvent, IdempotencyRecord
from apps.identity.permissions import MANAGEMENT_ROLES, IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from apps.identity.services import rate_limit
from common.api import CookieMutationAPIView, page_serializer
from common.idempotency import Conflict, remember, replay

from .models import (
    ExternalReceipt,
    OrderItem,
    ServiceRequest,
    ServiceSession,
    SessionLifecycleEvent,
    SessionPoint,
)
from .production import publish
from .services import OPEN_STATES

TERMINAL_ITEMS = ("DELIVERED", "CANCELLED", "REJECTED")


class SessionCommand(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


class ExternalReceiptInput(SessionCommand):
    point_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=16, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=ExternalReceipt.Method.choices)


class SessionReopenInput(SessionCommand):
    reason = serializers.CharField(max_length=300)


class ReceiptReverseInput(SessionReopenInput):
    pass


class ExternalReceiptOutput(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.name")
    staff_id = serializers.UUIDField(read_only=True)
    point_id = serializers.UUIDField(read_only=True)
    reverses_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = ExternalReceipt
        fields = [
            "id",
            "point_id",
            "staff_id",
            "staff_name",
            "method",
            "amount",
            "notes",
            "created_at",
            "reverses_id",
        ]


class LifecycleOutput(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.name")
    staff_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = SessionLifecycleEvent
        fields = [
            "id",
            "staff_id",
            "staff_name",
            "action",
            "reason",
            "consumption_total",
            "declared_received",
            "version",
            "points",
            "created_at",
        ]


class SettlementOutput(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    version = serializers.IntegerField()
    opened_at = serializers.DateTimeField()
    closed_at = serializers.DateTimeField(allow_null=True)
    consumption_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    declared_received = serializers.DecimalField(max_digits=16, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=16, decimal_places=2)
    outstanding_items = serializers.IntegerField()
    pending_calls = serializers.IntegerField()
    receipts = ExternalReceiptOutput(many=True)
    lifecycle = LifecycleOutput(many=True)
    declaration_notice = serializers.CharField()


def session_totals(session):
    consumption = OrderItem.objects.filter(batch__session=session).exclude(
        status__in=["CANCELLED", "REJECTED"]
    ).aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
    declared = session.external_receipts.aggregate(
        total=Sum(
            Case(
                When(reverses__isnull=False, then=-F("amount")),
                default=F("amount"),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )
    )["total"] or Decimal("0.00")
    return consumption, declared


def settlement_data(session):
    consumption, declared = session_totals(session)
    return {
        "id": str(session.id),
        "status": session.status,
        "version": session.version,
        "opened_at": session.opened_at.isoformat(),
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        "consumption_total": str(consumption),
        "declared_received": str(declared),
        "remaining": str(consumption - declared),
        "outstanding_items": OrderItem.objects.filter(batch__session=session)
        .exclude(status__in=TERMINAL_ITEMS)
        .count(),
        "pending_calls": ServiceRequest.objects.filter(
            session=session, status__in=["OPEN", "ASSIGNED"]
        ).count(),
        "receipts": ExternalReceiptOutput(
            session.external_receipts.select_related("staff"), many=True
        ).data,
        "lifecycle": LifecycleOutput(
            session.lifecycle_events.select_related("staff"), many=True
        ).data,
        "declaration_notice": "Recebimentos são declarações da equipe sobre valores recebidos fora do TapServe. O sistema não verifica bancos nem processa pagamentos.",
    }


def require_session_access(identity, permission=None):
    require_permission(identity, "VIEW_OPERATION")
    require_permission(identity, "VIEW_ALL_TABLES")
    if permission:
        require_permission(identity, permission)
    if permission in {"CORRECT_RECEIPT", "REOPEN_SESSION"} and (
        not identity.strong or identity.staff.role.name not in MANAGEMENT_ROLES
    ):
        raise PermissionDenied("A correção exige responsável autenticado com senha.")


def lock_session(identity, identifier):
    candidate = ServiceSession.objects.filter(id=identifier, unit=identity.staff.unit).first()
    if candidate is None:
        raise NotFound()
    point_ids = list(candidate.point_links.values_list("point_id", flat=True).distinct())
    # ASVS V15.4: every lifecycle mutation takes point locks before the session lock.
    points = list(
        ServicePoint.objects.select_for_update(of=("self",))
        .filter(id__in=point_ids, unit=identity.staff.unit)
        .order_by("id")
    )
    session = ServiceSession.objects.select_for_update(of=("self",)).get(
        id=identifier, unit=identity.staff.unit
    )
    if len(points) != len(point_ids) or not points:
        raise Conflict("O vínculo da mesa mudou. Atualize antes de continuar.")
    return session, points


def change_settlement(identity, identifier, data, action, *, receipt_id=None):
    permissions = {
        "RECEIPT": "REGISTER_PAYMENT",
        "REVERSE": "CORRECT_RECEIPT",
        "CLOSE": "CLOSE_SESSION",
        "REOPEN": "REOPEN_SESSION",
    }
    require_session_access(identity, permissions[action])
    rate_limit("settlement-staff:" + str(identity.staff.id), 30, 60)
    return _change_settlement(identity, identifier, data, action, receipt_id=receipt_id)


@transaction.atomic
def _change_settlement(identity, identifier, data, action, *, receipt_id):
    session, points = lock_session(identity, identifier)
    require_session_access(
        identity,
        {
            "RECEIPT": "REGISTER_PAYMENT",
            "REVERSE": "CORRECT_RECEIPT",
            "CLOSE": "CLOSE_SESSION",
            "REOPEN": "REOPEN_SESSION",
        }[action],
    )
    body = {**data, "receipt_id": str(receipt_id) if receipt_id else None}
    actor, operation = str(identity.staff.id), "SETTLEMENT_" + action
    previous = replay(actor, operation, str(session.id), data["idempotency_key"], body)
    if previous:
        return previous.response
    if session.version != data["expected_version"]:
        raise Conflict("O atendimento mudou. Confira os valores atuais antes de continuar.")
    if action == "REOPEN":
        reopen_session(session, points, data["reason"])
    else:
        if session.status not in OPEN_STATES:
            raise Conflict("O atendimento está encerrado. Nenhum registro foi alterado.")
        if action == "RECEIPT":
            register_receipt(identity, session, points, data)
        elif action == "REVERSE":
            reverse_receipt(identity, session, receipt_id, data["reason"])
        elif action == "CLOSE":
            close_session(session, points)
    session.version += 1
    session.save(update_fields=["status", "closed_at", "check_requested_at", "version"])
    consumption, declared = session_totals(session)
    if action in {"CLOSE", "REOPEN"}:
        SessionLifecycleEvent.objects.create(
            session=session,
            staff=identity.staff,
            action=action,
            reason=data["reason"],
            consumption_total=consumption,
            declared_received=declared,
            version=session.version,
            points=[{"id": str(p.id), "name": p.label} for p in points],
        )
    AuditEvent.objects.create(
        unit=session.unit,
        staff=identity.staff,
        action=operation,
        resource_id=str(session.id),
        reason=data["reason"],
        details={
            "consumption_total": str(consumption),
            "declared_received": str(declared),
            "version": session.version,
            "receipt_id": body["receipt_id"],
        },
    )
    for point in points:
        publish(session, "SESSION_" + action, [], point=point)
    result = settlement_data(session)
    remember(
        session.unit, actor, operation, str(session.id), data["idempotency_key"], body, result, 200
    )
    return result


def register_receipt(identity, session, points, data):
    point = next((p for p in points if p.id == data["point_id"]), None)
    if (
        point is None
        or not SessionPoint.objects.filter(
            session=session, point=point, ended_at__isnull=True
        ).exists()
    ):
        raise ValidationError({"point_id": "Selecione uma mesa ativa deste atendimento."})
    consumption, declared = session_totals(session)
    if data["amount"] > consumption - declared:
        raise Conflict(
            "O valor informado excede o saldo operacional. Confira ou corrija os registros anteriores."
        )
    if session.external_receipts.filter(reverses__isnull=True).count() >= 500:
        raise Conflict("Limite de lançamentos atingido. Solicite ajuda ao responsável.")
    ExternalReceipt.objects.create(
        session=session,
        point=point,
        staff=identity.staff,
        amount=data["amount"],
        method=data["method"],
        notes=data["reason"],
    )


def reverse_receipt(identity, session, identifier, reason):
    original = ExternalReceipt.objects.filter(
        id=identifier, session=session, reverses__isnull=True
    ).first()
    if original is None:
        raise NotFound()
    if ExternalReceipt.objects.filter(reverses=original).exists():
        raise Conflict("Este lançamento já foi revertido.")
    ExternalReceipt.objects.create(
        session=session,
        point=original.point,
        staff=identity.staff,
        amount=original.amount,
        method=original.method,
        notes=reason,
        reverses=original,
    )


def close_session(session, points):
    if OrderItem.objects.filter(batch__session=session).exclude(status__in=TERMINAL_ITEMS).exists():
        raise Conflict("Conclua a entrega ou cancele os itens pendentes antes de encerrar a mesa.")
    consumption, declared = session_totals(session)
    if consumption != declared:
        raise Conflict(
            "O saldo operacional precisa ser zero. Registre o recebimento externo ou corrija os lançamentos antes de encerrar."
        )
    now = timezone.now()
    point_ids = [p.id for p in points]
    device_ids = list(
        DeviceAccess.objects.filter(
            Q(session=session) | Q(point_id__in=point_ids, session__isnull=True)
        ).values_list("id", flat=True)
    )
    DeviceAccess.objects.filter(id__in=device_ids, revoked_at__isnull=True).update(revoked_at=now)
    from apps.access.admission import invalidate_admissions

    from .models import RealtimeLease

    invalidate_admissions(point_ids, session_id=session.id)
    RealtimeLease.objects.filter(actor__in=["D:" + str(value) for value in device_ids]).delete()
    SessionPoint.objects.filter(session=session, ended_at__isnull=True).update(ended_at=now)
    calls = ServiceRequest.objects.filter(
        Q(session=session) | Q(point_id__in=point_ids, session__isnull=True),
        status__in=["OPEN", "ASSIGNED"],
    )
    for call in calls:
        AuditEvent.objects.create(
            unit=session.unit,
            action="CALL_CLOSED_WITH_SESSION",
            resource_id=str(call.id),
            reason="Encerramento do atendimento.",
            details={"previous_status": call.status, "session_id": str(session.id)},
        )
    calls.update(status="CANCELLED", updated_at=now)
    session.status = "CLOSED"
    session.closed_at = now


def reopen_session(session, points, reason):
    if not reason.strip():
        raise ValidationError({"reason": "Informe por que o mesmo atendimento precisa continuar."})
    if session.status != "CLOSED" or session.closed_at is None:
        raise Conflict("Somente um atendimento encerrado pode ser reaberto.")
    if any(not p.active for p in points):
        raise Conflict("Reative os pontos de atendimento antes de reabrir.")
    # Never restore an old party after a newer party occupied any of its points.
    if (
        SessionPoint.objects.filter(point__in=points)
        .filter(Q(ended_at__isnull=True) | Q(activated_at__gt=session.closed_at))
        .exists()
    ):
        raise Conflict(
            "A mesa já recebeu outro atendimento. O histórico encerrado será preservado."
        )
    SessionPoint.objects.bulk_create([SessionPoint(session=session, point=p) for p in points])
    session.status = "REOPENED"
    session.closed_at = None
    session.check_requested_at = None


class StaffSessionSettlementView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=SettlementOutput)
    def get(self, request, identifier):
        require_session_access(request.auth)
        session = ServiceSession.objects.filter(id=identifier, unit=request.auth.staff.unit).first()
        if session is None:
            raise NotFound()
        return Response(settlement_data(session))


class ExternalReceiptView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=ExternalReceiptInput, responses=SettlementOutput)
    def post(self, request, identifier):
        data = ExternalReceiptInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_settlement(request.auth, identifier, data.validated_data, "RECEIPT"))


class ExternalReceiptReverseView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=ReceiptReverseInput, responses=SettlementOutput)
    def post(self, request, identifier, receipt_id):
        data = ReceiptReverseInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            change_settlement(
                request.auth, identifier, data.validated_data, "REVERSE", receipt_id=receipt_id
            )
        )


class SessionCloseView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=SessionCommand, responses=SettlementOutput)
    def post(self, request, identifier):
        data = SessionCommand(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_settlement(request.auth, identifier, data.validated_data, "CLOSE"))


class SessionReopenView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=SessionReopenInput, responses=SettlementOutput)
    def post(self, request, identifier):
        data = SessionReopenInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_settlement(request.auth, identifier, data.validated_data, "REOPEN"))


class CommandResultQuery(StrictSerializer):
    action = serializers.ChoiceField(choices=["RECEIPT", "REVERSE", "CLOSE", "REOPEN"])


class CommandResultOutput(serializers.Serializer):
    applied = serializers.BooleanField()
    version = serializers.IntegerField()
    result = SettlementOutput(allow_null=True)


class SettlementCommandResultView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(parameters=[CommandResultQuery], responses=CommandResultOutput)
    @transaction.atomic
    def get(self, request, identifier, key):
        require_session_access(request.auth)
        query = CommandResultQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        session, _ = lock_session(request.auth, identifier)
        record = IdempotencyRecord.objects.filter(
            unit=request.auth.staff.unit,
            actor=str(request.auth.staff.id),
            resource=str(session.id),
            action="SETTLEMENT_" + query.validated_data["action"],
            key=key,
        ).first()
        return Response(
            {
                "applied": record is not None,
                "version": session.version,
                "result": record.response if record else None,
            }
        )


class SessionHistoryOutput(serializers.ModelSerializer):
    point_names = serializers.SerializerMethodField()

    def get_point_names(self, session) -> list[str]:
        return sorted({link.point.label for link in session.point_links.all()})

    class Meta:
        model = ServiceSession
        fields = ["id", "status", "version", "opened_at", "closed_at", "point_names"]


class HistoryQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)


class PointSessionHistoryView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(parameters=[HistoryQuery], responses=page_serializer(SessionHistoryOutput))
    def get(self, request, identifier):
        require_session_access(request.auth)
        query = HistoryQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        if not ServicePoint.objects.filter(id=identifier, unit=request.auth.staff.unit).exists():
            raise NotFound()
        sessions = (
            ServiceSession.objects.filter(
                unit=request.auth.staff.unit, point_links__point_id=identifier
            )
            .distinct()
            .prefetch_related("point_links__point")
            .order_by("-opened_at", "id")
        )
        pager = PageNumberPagination()
        return pager.get_paginated_response(
            SessionHistoryOutput(pager.paginate_queryset(sessions, request), many=True).data
        )

"""Calls can precede the first order; ownership is claimed atomically per point."""

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.access.models import ServicePoint
from apps.access.views import PublicView
from apps.identity.models import AuditEvent, IdempotencyRecord
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from apps.identity.services import rate_limit
from common.api import CookieMutationAPIView, page_serializer
from common.idempotency import Conflict, remember, replay

from .models import ServiceRequest, ServiceSession
from .production import publish
from .services import OPEN_STATES, require_device


class RequestInput(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=ServiceRequest.Kind.choices)
    message = serializers.CharField(max_length=300, allow_blank=True, default="")

    def validate(self, data):
        if data["kind"] == "OTHER" and not data["message"]:
            raise ValidationError("Descreva a solicitação.")
        return data


class RequestQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    status = serializers.ChoiceField(
        choices=["PENDING", "ALL", *ServiceRequest.State.values], default="PENDING"
    )
    kind = serializers.ChoiceField(choices=ServiceRequest.Kind.choices, required=False)
    point = serializers.UUIDField(required=False)


class RequestCommand(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    expected_status = serializers.ChoiceField(choices=ServiceRequest.State.choices)


class StaffRequestCommand(RequestCommand):
    status = serializers.ChoiceField(choices=["ASSIGNED", "RESOLVED", "CANCELLED"])
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


class RequestOutput(serializers.ModelSerializer):
    point_name = serializers.CharField(source="point.label")
    assignee_name = serializers.CharField(source="assigned_to.name", allow_null=True)
    can_customer_cancel = serializers.SerializerMethodField()

    def get_can_customer_cancel(self, call) -> bool:
        device = self.context.get("device")
        return bool(
            device is not None
            and device.id == call.device_id
            and call.kind != "CHECK"
            and call.status in {"OPEN", "ASSIGNED"}
        )

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "kind",
            "message",
            "status",
            "point_id",
            "point_name",
            "session_id",
            "assigned_to_id",
            "assignee_name",
            "created_at",
            "updated_at",
            "can_customer_cancel",
        ]


def requests(scope):
    return (
        ServiceRequest.objects.filter(**scope)
        .select_related("point", "assigned_to")
        .order_by("created_at", "id")
    )


def create_request(device, data: dict) -> dict:
    rate_limit("call-device:" + str(device.id), 5, 60)
    rate_limit("call-unit:" + str(device.point.unit_id), 30, 60)
    return _create_request(device, data)


@transaction.atomic
def _create_request(device, data):
    point = (
        ServicePoint.objects.select_for_update(of=("self",))
        .select_related("unit__company")
        .get(id=device.point_id)
    )
    device = require_device(device, point)
    session = (
        ServiceSession.objects.select_for_update(of=("self",)).filter(id=device.session_id).first()
        if device.session_id is not None
        else None
    )
    if session is not None and session.status not in OPEN_STATES:
        raise Conflict()
    previous = replay(str(device.id), "CALL_CREATE", str(point.id), data["idempotency_key"], data)
    if previous:
        return previous.response
    if data["kind"] == "PACKAGING" and (
        not point.unit.leftover_packaging_enabled or session is None
    ):
        raise ValidationError(
            {"kind": "Embalagem de sobras não está disponível neste atendimento."}
        )
    if data["kind"] == "CHECK":
        if session is None:
            raise ValidationError("A conta fica disponível após o primeiro pedido confirmado.")
        if session.status not in {"OPEN", "REOPENED"}:
            raise Conflict("A conta já foi solicitada ou está em fechamento.")
        session.status = "CHECK_REQUESTED"
        session.check_requested_at = timezone.now()
        session.version += 1
        session.save(update_fields=["status", "check_requested_at", "version"])
    if ServiceRequest.objects.filter(
        point=point, kind=data["kind"], status__in=["OPEN", "ASSIGNED"]
    ).exists():
        raise Conflict("Já existe um chamado deste tipo aguardando atendimento.")
    call = ServiceRequest.objects.create(
        unit=point.unit,
        point=point,
        session=session,
        device=device,
        kind=data["kind"],
        message=data["message"],
    )
    AuditEvent.objects.create(
        unit=point.unit,
        device=device,
        action="CALL_OPENED",
        resource_id=str(call.id),
        details={"kind": call.kind, "status": call.status},
    )
    publish(session, "CALL_OPENED", [], point=point)
    result = dict(RequestOutput(call, context={"device": device}).data)
    remember(
        point.unit,
        str(device.id),
        "CALL_CREATE",
        str(point.id),
        data["idempotency_key"],
        data,
        result,
        201,
    )
    return result


def change_request(identity, identifier, data: dict, *, manual=False) -> dict:
    actor = str(identity.staff.id if manual else identity.id)
    rate_limit("call-change:" + actor, 30, 60)
    return _change_request(identity, identifier, data, manual=manual)


@transaction.atomic
def _change_request(identity, identifier, data, *, manual):
    if manual:
        require_permission(identity, "ASSIGN_SERVICE_REQUEST")
        require_permission(identity, "VIEW_OPERATION")
        scope = {"unit": identity.staff.unit}
        device = None
    else:
        scope = {"device": identity, "point_id": identity.point_id}
    candidate = ServiceRequest.objects.filter(id=identifier, **scope).first()
    if candidate is None:
        raise NotFound()
    point = (
        ServicePoint.objects.select_for_update(of=("self",))
        .select_related("unit__company")
        .get(id=candidate.point_id)
    )
    if not manual:
        device = require_device(identity, point)
    # Order and call creation also lock point before session, preventing attachment races.
    candidate.refresh_from_db()
    session = (
        ServiceSession.objects.select_for_update(of=("self",))
        .filter(id=candidate.session_id)
        .first()
        if candidate.session_id is not None
        else None
    )
    call = (
        ServiceRequest.objects.select_for_update(of=("self",))
        .select_related("point", "assigned_to")
        .get(id=identifier)
    )
    if call.session_id != candidate.session_id or (
        session is not None and session.status not in OPEN_STATES
    ):
        raise Conflict()
    if manual:
        require_permission(identity, "ASSIGN_SERVICE_REQUEST")
    actor = str(identity.staff.id if manual else identity.id)
    previous = replay(actor, "CALL_CHANGE", str(call.id), data["idempotency_key"], data)
    if previous:
        return previous.response
    target = data["status"] if manual else "CANCELLED"
    if not manual and call.kind == "CHECK":
        raise PermissionDenied("Solicite à equipe qualquer alteração na conta.")
    if call.status != data["expected_status"] or call.status not in {"OPEN", "ASSIGNED"}:
        raise Conflict()
    if target == "ASSIGNED":
        if call.status != "OPEN":
            raise Conflict()
        call.assigned_to = identity.staff
    elif target == "RESOLVED":
        if call.status != "ASSIGNED" or call.assigned_to_id != identity.staff.id:
            raise PermissionDenied()
    before = call.status
    call.status = target
    call.save(update_fields=["status", "assigned_to", "updated_at"])
    if (
        call.kind == "CHECK"
        and target == "CANCELLED"
        and session is not None
        and session.status == "CHECK_REQUESTED"
    ):
        session.status = "OPEN"
        session.check_requested_at = None
        session.version += 1
        session.save(update_fields=["status", "check_requested_at", "version"])
    AuditEvent.objects.create(
        unit=call.unit,
        staff=identity.staff if manual else None,
        device=device,
        action="CALL_" + target,
        resource_id=str(call.id),
        reason=data.get("reason", ""),
        details={"before": before, "after": target, "assigned_to_id": call.assigned_to_id},
    )
    publish(session, "CALL_" + target, [], point=point)
    result = dict(RequestOutput(call, context={"device": device}).data)
    remember(
        call.unit, actor, "CALL_CHANGE", str(call.id), data["idempotency_key"], data, result, 200
    )
    return result


class PublicRequestsView(PublicView):
    @extend_schema(responses=page_serializer(RequestOutput))
    def get(self, request):
        pager = PageNumberPagination()
        page: list[ServiceRequest] | None = pager.paginate_queryset(
            requests(
                {
                    "point_id": request.auth.point_id,
                    "session_id": request.auth.session_id,
                    "status__in": ["OPEN", "ASSIGNED"],
                }
            ),
            request,
        )
        return pager.get_paginated_response(
            RequestOutput(page, many=True, context={"device": request.auth}).data
        )

    @extend_schema(request=RequestInput, responses={201: RequestOutput})
    def post(self, request):
        data = RequestInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(create_request(request.auth, data.validated_data), status=201)


class PublicRequestCancelView(PublicView):
    @extend_schema(request=RequestCommand, responses=RequestOutput)
    def post(self, request, identifier):
        data = RequestCommand(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_request(request.auth, identifier, data.validated_data))


class PublicRequestReceiptView(PublicView):
    @extend_schema(responses=RequestOutput)
    def get(self, request, key):
        previous = IdempotencyRecord.objects.filter(
            unit=request.auth.point.unit,
            actor=str(request.auth.id),
            resource=str(request.auth.point_id),
            action="CALL_CREATE",
            key=key,
        ).first()
        if previous is None:
            raise NotFound()
        return Response(previous.response)


class StaffRequestsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=page_serializer(RequestOutput))
    def get(self, request):
        require_permission(request.auth, "VIEW_OPERATION")
        require_permission(request.auth, "ASSIGN_SERVICE_REQUEST")
        query = RequestQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        scope = {"unit": request.auth.staff.unit}
        data = query.validated_data
        if data["status"] == "PENDING":
            scope["status__in"] = ["OPEN", "ASSIGNED"]
        elif data["status"] != "ALL":
            scope["status"] = data["status"]
        if "kind" in data:
            scope["kind"] = data["kind"]
        if "point" in data:
            scope["point_id"] = data["point"]
        pager = PageNumberPagination()
        page: list[ServiceRequest] | None = pager.paginate_queryset(requests(scope), request)
        return pager.get_paginated_response(RequestOutput(page, many=True).data)


class StaffRequestStatusView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=StaffRequestCommand, responses=RequestOutput)
    def post(self, request, identifier):
        data = StaffRequestCommand(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_request(request.auth, identifier, data.validated_data, manual=True))

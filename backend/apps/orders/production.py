"""Explicit sector grants and one locked transition per item, with immutable history."""

from django.db import connection, transaction
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.catalog.models import ProductionSector
from apps.catalog.serializers import SectorOutput
from apps.identity.models import AuditEvent, Staff
from apps.identity.permissions import MANAGEMENT_ROLES, IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from apps.identity.services import rate_limit
from apps.organizations.models import Unit
from common.api import CookieMutationAPIView, page_serializer
from common.idempotency import Conflict, remember, replay

from .models import (
    DomainEvent,
    ItemStatusEvent,
    OrderItem,
    ProductionAssignment,
    ServiceSession,
    SessionPoint,
)
from .serializers import ItemOutput
from .services import OPEN_STATES


def publish(session, kind: str, sector_ids, *, point=None) -> DomainEvent:
    if not connection.in_atomic_block:
        raise RuntimeError("Domain publication must share its mutation transaction")
    event = DomainEvent.objects.create(
        unit=session.unit if session is not None else point.unit,
        session=session,
        point=point,
        kind=kind,
        version=session.version if session is not None else 1,
        sector_ids=sorted(str(value) for value in set(sector_ids)),
    )
    # The database trigger delivers only at commit; rollback leaves no notification.
    return event


class StatusInput(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    expected_status = serializers.ChoiceField(choices=OrderItem.State.choices)
    status = serializers.ChoiceField(
        choices=["ACCEPTED", "REJECTED", "PREPARING", "READY", "DELIVERING", "DELIVERED"]
    )
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


class ProductionQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    sector = serializers.UUIDField(required=False)


class SectorAssignmentInput(StrictSerializer):
    sector_ids = serializers.ListField(child=serializers.UUIDField(), max_length=20)
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


class SectorAssignmentOutput(serializers.Serializer):
    sector_ids = serializers.ListField(child=serializers.UUIDField())
    sectors = SectorOutput(many=True, read_only=True)


class ProductionItemOutput(ItemOutput):
    session_id = serializers.UUIDField(source="batch.session_id", read_only=True)
    point_names = serializers.SerializerMethodField()

    def get_point_names(self, item) -> list[str]:
        return [
            link.point.label
            for link in item.batch.session.point_links.all()
            if link.ended_at is None
        ]

    class Meta(ItemOutput.Meta):
        fields = [*ItemOutput.Meta.fields, "session_id", "point_names"]


def assigned_sectors(identity):
    # Unit-wide production requires both managerial responsibility and explicit effective grants.
    if identity.staff.role.name in MANAGEMENT_ROLES and identity.allows("VIEW_ALL_TABLES"):
        return ProductionSector.objects.filter(unit=identity.staff.unit, active=True).values_list(
            "id", flat=True
        )
    return ProductionAssignment.objects.filter(
        staff=identity.staff, sector__active=True, sector__unit=identity.staff.unit
    ).values_list("sector_id", flat=True)


def work_items(unit):
    return (
        OrderItem.objects.filter(batch__session__unit=unit, batch__session__status__in=OPEN_STATES)
        .select_related("participant", "batch__session__unit")
        .prefetch_related(
            Prefetch(
                "batch__session__point_links",
                queryset=SessionPoint.objects.filter(ended_at__isnull=True).select_related("point"),
            )
        )
        .order_by("created_at", "id")
    )


@transaction.atomic
def set_sectors(identity, identifier, data):
    require_permission(identity, "MANAGE_STAFF")
    Unit.objects.select_for_update().get(id=identity.staff.unit_id)
    staff = (
        Staff.objects.select_for_update().filter(id=identifier, unit=identity.staff.unit).first()
    )
    if staff is None:
        raise NotFound()
    ids = data["sector_ids"]
    if len(ids) != len(set(ids)) or ProductionSector.objects.filter(
        id__in=ids, unit=staff.unit, active=True
    ).count() != len(ids):
        raise ValidationError("Setores inválidos nesta unidade.")
    ProductionAssignment.objects.filter(staff=staff).delete()
    ProductionAssignment.objects.bulk_create(
        [ProductionAssignment(staff=staff, sector_id=identifier) for identifier in ids]
    )
    AuditEvent.objects.create(
        unit=staff.unit,
        staff=identity.staff,
        action="STAFF_SECTORS_UPDATED",
        resource_id=str(staff.id),
        reason=data["reason"],
    )
    return {
        "sector_ids": [str(value) for value in ids],
        "sectors": SectorOutput(
            ProductionSector.objects.filter(id__in=ids, unit=staff.unit).order_by("name", "id"),
            many=True,
        ).data,
    }


def transition(identity, identifier, data):
    rate_limit("item-actor:" + str(identity.staff.id), 60, 60)
    return _transition(identity, identifier, data)


@transaction.atomic
def _transition(identity, identifier, data):
    candidate = OrderItem.objects.filter(
        id=identifier, batch__session__unit=identity.staff.unit
    ).first()
    if candidate is None:
        raise NotFound()
    session = ServiceSession.objects.select_for_update().get(id=candidate.batch.session_id)
    item = OrderItem.objects.select_for_update().get(id=candidate.id)
    if session.status not in OPEN_STATES:
        raise Conflict()
    target = data["status"]
    code = (
        "CLAIM_DELIVERY"
        if target == "DELIVERING"
        else "COMPLETE_DELIVERY"
        if target == "DELIVERED"
        else "UPDATE_PRODUCTION_STATUS"
    )
    require_permission(identity, "VIEW_OPERATION")
    require_permission(identity, code)
    if code == "UPDATE_PRODUCTION_STATUS" and item.sector_id not in assigned_sectors(identity):
        raise PermissionDenied()
    previous = replay(
        str(identity.staff.id), "ITEM_STATUS", str(item.id), data["idempotency_key"], data
    )
    if previous:
        return previous.response
    allowed = {
        "NEW": {"ACCEPTED", "REJECTED"},
        "ACCEPTED": {"PREPARING"},
        "PREPARING": {"READY"},
        "READY": {"DELIVERING"},
        "DELIVERING": {"DELIVERED"},
    }
    if item.status != data["expected_status"] or target not in allowed.get(item.status, set()):
        raise Conflict()
    if target == "DELIVERED" and item.delivered_by_id != identity.staff.id:
        raise PermissionDenied()
    old = item.status
    item.status = target
    item.version += 1
    if target == "DELIVERING":
        item.delivered_by = identity.staff
    item.save(update_fields=["status", "version", "delivered_by", "updated_at"])
    ItemStatusEvent.objects.create(
        item=item,
        staff=identity.staff,
        previous_status=old,
        status=target,
        reason=data.get("reason", ""),
    )
    session.version += 1
    session.save(update_fields=["version"])
    AuditEvent.objects.create(
        unit=session.unit,
        staff=identity.staff,
        action="ITEM_" + target,
        resource_id=str(item.id),
        reason=data.get("reason", ""),
        details={"previous_status": old, "status": target},
    )
    publish(session, "ITEM_STATUS_CHANGED", [item.sector_id])
    result = dict(ItemOutput(item).data)
    remember(
        session.unit,
        str(identity.staff.id),
        "ITEM_STATUS",
        str(item.id),
        data["idempotency_key"],
        data,
        result,
        200,
    )
    return result


class StaffSectorsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=SectorAssignmentOutput)
    def get(self, request, identifier):
        require_permission(request.auth, "MANAGE_STAFF")
        staff = Staff.objects.filter(id=identifier, unit=request.auth.staff.unit).first()
        if staff is None:
            raise NotFound()
        return Response(
            {
                "sector_ids": list(
                    staff.production_assignments.values_list("sector_id", flat=True)
                ),
                "sectors": SectorOutput(
                    ProductionSector.objects.filter(productionassignment__staff=staff).order_by(
                        "name", "id"
                    ),
                    many=True,
                ).data,
            }
        )

    @extend_schema(request=SectorAssignmentInput, responses=SectorAssignmentOutput)
    def put(self, request, identifier):
        data = SectorAssignmentInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(set_sectors(request.auth, identifier, data.validated_data))


class SectorOptionsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=page_serializer(SectorOutput))
    def get(self, request):
        require_permission(request.auth, "MANAGE_STAFF")
        search = request.query_params.get("search", "")
        if len(search) > 100:
            raise ValidationError("Busca muito longa.")
        sectors = ProductionSector.objects.filter(
            unit=request.auth.staff.unit, active=True, name__icontains=search
        ).order_by("name", "id")
        pager = PageNumberPagination()
        page = pager.paginate_queryset(sectors, request)
        return pager.get_paginated_response(SectorOutput(page, many=True).data)


class ProductionItemsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(parameters=[ProductionQuery], responses=page_serializer(ProductionItemOutput))
    def get(self, request):
        require_permission(request.auth, "VIEW_OPERATION")
        require_permission(request.auth, "UPDATE_PRODUCTION_STATUS")
        query = ProductionQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        items = work_items(request.auth.staff.unit).filter(
            sector_id__in=assigned_sectors(request.auth),
            status__in=["NEW", "ACCEPTED", "PREPARING", "READY"],
        )
        if "sector" in query.validated_data:
            identifier = query.validated_data["sector"]
            if identifier not in assigned_sectors(request.auth):
                raise NotFound()
            items = items.filter(sector_id=identifier)
        pager = PageNumberPagination()
        page: list[OrderItem] | None = pager.paginate_queryset(items, request)
        return pager.get_paginated_response(ProductionItemOutput(page, many=True).data)


class ItemStatusView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=StatusInput, responses=ItemOutput)
    def post(self, request, identifier):
        data = StatusInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(transition(request.auth, identifier, data.validated_data))

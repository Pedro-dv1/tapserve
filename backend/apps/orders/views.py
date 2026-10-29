from decimal import Decimal

from django.db.models import Count, Prefetch, Q, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.access.models import ServicePoint
from apps.access.serializers import PointOutput
from apps.access.services import live_devices
from apps.access.views import PublicView
from apps.catalog.serializers import PublicMenuProductOutput
from apps.catalog.services import point_menu
from apps.catalog.views import popular_products
from apps.identity.models import IdempotencyRecord
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from common.api import CookieMutationAPIView, page_serializer

from .models import OrderBatch, OrderItem, ServiceRequest, ServiceSession, SessionPoint
from .production import ProductionItemOutput, work_items
from .serializers import (
    BatchOutput,
    ManualOrderInput,
    OrderInput,
    OrderReceiptOutput,
    ParticipantInput,
    ParticipantOutput,
    PublicSessionContext,
    SessionOutput,
)
from .services import (
    OPEN_STATES,
    create_participant,
    remove_participant,
    session_data,
    submit_order,
)


class OperationQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    search = serializers.CharField(max_length=100, allow_blank=True, default="")


class StaffOrderQuery(OperationQuery):
    status = serializers.ChoiceField(choices=OrderItem.State.choices, required=False)


class OperationSessionOutput(SessionOutput):
    item_counts = serializers.DictField(child=serializers.IntegerField())


class DeliveryQuery(OperationQuery):
    status = serializers.ChoiceField(choices=["READY", "DELIVERING"], required=False)


def batches(scope):
    return (
        OrderBatch.objects.filter(**scope)
        .select_related("session__unit", "staff")
        .prefetch_related(
            "session__point_links__point",
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related(
                    "participant", "batch__session__unit"
                ).order_by("created_at", "id"),
            ),
        )
        .order_by("-created_at", "id")
    )


class PublicOrdersView(PublicView):
    @extend_schema(request=OrderInput, responses={201: OrderReceiptOutput})
    def post(self, request):
        data = OrderInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(submit_order(request.auth, data.validated_data), status=201)

    @extend_schema(responses=page_serializer(BatchOutput))
    def get(self, request):
        pager = PageNumberPagination()
        page = pager.paginate_queryset(
            batches({"session_id": request.auth.session_id})
            if request.auth.session_id
            else OrderBatch.objects.none(),
            request,
        )
        return pager.get_paginated_response(
            BatchOutput(page, many=True, context={"device": request.auth}).data
        )


class PublicOrderReceiptView(PublicView):
    @extend_schema(responses=OrderReceiptOutput)
    def get(self, request, key):
        record = IdempotencyRecord.objects.filter(
            unit=request.auth.point.unit, actor=str(request.auth.id), action="ORDER", key=key
        ).first()
        if record is None:
            raise NotFound()
        return Response(record.response)


class PublicSessionView(PublicView):
    @extend_schema(responses=PublicSessionContext)
    def get(self, request):
        session = (
            ServiceSession.objects.filter(
                id=request.auth.session_id, unit=request.auth.point.unit, status__in=OPEN_STATES
            )
            .select_related("unit")
            .prefetch_related("point_links__point", "participants")
            .first()
            if request.auth.session_id
            else None
        )
        return Response(
            {
                "session": session_data(session) if session else None,
                "point_status": "OCCUPIED" if session else "FREE",
                "point": PointOutput(request.auth.point).data,
                "leftover_packaging_enabled": request.auth.point.unit.leftover_packaging_enabled,
            }
        )


class PublicParticipantsView(PublicView):
    @extend_schema(request=ParticipantInput, responses={201: ParticipantOutput})
    def post(self, request):
        data = ParticipantInput(data=request.data)
        data.is_valid(raise_exception=True)
        participant = create_participant(request.auth, data.validated_data["display_name"])
        return Response(ParticipantOutput(participant).data, status=201)


class CanCreateManualOrder(IsActiveStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.auth.allows("CREATE_MANUAL_ORDER")


class PublicParticipantDetailView(PublicView):
    @extend_schema(request=StrictSerializer, responses={204: None})
    def delete(self, request, identifier):
        data = StrictSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        remove_participant(request.auth, identifier)
        return Response(status=204)


class ManualOrderView(CookieMutationAPIView):
    permission_classes = [CanCreateManualOrder]

    def get_permissions(self):
        return [
            CanViewOperation() if self.request.method in {"GET", "HEAD"} else CanCreateManualOrder()
        ]

    @extend_schema(parameters=[StaffOrderQuery], responses=page_serializer(BatchOutput))
    def get(self, request):
        return staff_orders(request)

    @extend_schema(request=ManualOrderInput, responses={201: OrderReceiptOutput})
    def post(self, request):
        data = ManualOrderInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(submit_order(request.auth, data.validated_data, manual=True), status=201)


class CanViewOperation(IsActiveStaff):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.auth.allows("VIEW_OPERATION")
            and request.auth.allows("VIEW_ALL_TABLES")
        )


def staff_orders(request):
    require_permission(request.auth, "VIEW_OPERATION")
    require_permission(request.auth, "VIEW_ALL_TABLES")
    query = StaffOrderQuery(data=request.query_params)
    query.is_valid(raise_exception=True)
    rows = batches({"session__unit": request.auth.staff.unit})
    if "status" in query.validated_data:
        rows = rows.filter(items__status=query.validated_data["status"]).distinct()
    search = query.validated_data["search"]
    if search:
        rows = rows.filter(session__point_links__point__name__icontains=search).distinct()
    pager = PageNumberPagination()
    page: list[OrderBatch] | None = pager.paginate_queryset(rows, request)
    return pager.get_paginated_response(BatchOutput(page, many=True).data)


class TableQuery(OperationQuery):
    filter = serializers.ChoiceField(
        choices=["ALL", "OPEN", "CHECK", "CLEANING", "CUTLERY", "PACKAGING"], default="ALL"
    )


class OperationalPointOutput(PointOutput):
    session = SessionOutput(allow_null=True)
    connected_devices = serializers.IntegerField()
    order_count = serializers.IntegerField()
    active_order_count = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=16, decimal_places=2)
    pending_calls = serializers.ListField(child=serializers.DictField())

    class Meta(PointOutput.Meta):
        fields = [
            *PointOutput.Meta.fields,
            "session",
            "connected_devices",
            "order_count",
            "active_order_count",
            "subtotal",
            "pending_calls",
        ]


class StaffTablesView(CookieMutationAPIView):
    permission_classes = [CanViewOperation]

    @extend_schema(parameters=[TableQuery], responses=page_serializer(OperationalPointOutput))
    def get(self, request):
        query = TableQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        points = ServicePoint.objects.filter(unit=request.auth.staff.unit, active=True).order_by(
            "number", "name", "id"
        )
        if data["search"]:
            points = points.filter(
                Q(name__icontains=data["search"])
                | (
                    Q(number=int(data["search"]))
                    if data["search"].isdigit() and len(data["search"]) <= 6
                    else Q(pk__in=[])
                )
            )
        if data["filter"] == "OPEN":
            points = points.filter(
                id__in=SessionPoint.objects.filter(
                    ended_at__isnull=True, session__status__in=OPEN_STATES
                ).values("point_id")
            )
        elif data["filter"] != "ALL":
            points = points.filter(
                id__in=ServiceRequest.objects.filter(
                    unit=request.auth.staff.unit,
                    kind=data["filter"],
                    status__in=["OPEN", "ASSIGNED"],
                ).values("point_id")
            )
        pager = PageNumberPagination()
        page = list(pager.paginate_queryset(points, request) or [])
        links = list(
            SessionPoint.objects.filter(
                point__in=page, ended_at__isnull=True, session__status__in=OPEN_STATES
            )
            .select_related("session__unit")
            .prefetch_related("session__point_links__point", "session__participants")
        )
        sessions = {link.point_id: link.session for link in links}
        session_ids = {session.id for session in sessions.values()}
        counts = {
            row["session_id"]: row
            for row in OrderBatch.objects.filter(session_id__in=session_ids)
            .values("session_id")
            .annotate(
                total=Count("id", distinct=True),
                active=Count(
                    "id", distinct=True, filter=~Q(items__status__in=["CANCELLED", "REJECTED"])
                ),
            )
        }
        totals = {
            row["batch__session_id"]: row["total"]
            for row in OrderItem.objects.filter(batch__session_id__in=session_ids)
            .exclude(status__in=["CANCELLED", "REJECTED"])
            .values("batch__session_id")
            .annotate(total=Sum("line_total"))
        }
        devices = list(
            live_devices(request.auth.staff.unit)
            .filter(Q(session_id__in=session_ids) | Q(point__in=page, session__isnull=True))
            .values("point_id", "session_id")
            .annotate(total=Count("id"))
        )
        calls = list(
            ServiceRequest.objects.filter(
                unit=request.auth.staff.unit, point__in=page, status__in=["OPEN", "ASSIGNED"]
            ).values("id", "point_id", "kind", "created_at")
        )
        results = []
        for point in page:
            session = sessions.get(point.id)
            summary = counts.get(session.id) if session else None
            results.append(
                {
                    **PointOutput(point).data,
                    "session": session_data(session) if session else None,
                    "connected_devices": sum(
                        row["total"] for row in devices if row["session_id"] == session.id
                    )
                    if session
                    else sum(
                        row["total"]
                        for row in devices
                        if row["point_id"] == point.id and row["session_id"] is None
                    ),
                    "order_count": summary["total"] if summary else 0,
                    "active_order_count": summary["active"] if summary else 0,
                    "subtotal": str(totals.get(session.id, Decimal("0.00"))) if session else "0.00",
                    "pending_calls": [
                        {
                            "id": str(call["id"]),
                            "kind": call["kind"],
                            "created_at": call["created_at"],
                        }
                        for call in calls
                        if call["point_id"] == point.id
                    ],
                }
            )
        return pager.get_paginated_response(results)


class StaffPointMenuView(CookieMutationAPIView):
    permission_classes = [CanCreateManualOrder]

    @extend_schema(parameters=[OperationQuery], responses=page_serializer(PublicMenuProductOutput))
    def get(self, request, identifier):
        point = ServicePoint.objects.filter(
            id=identifier, unit=request.auth.staff.unit, active=True
        ).first()
        if point is None:
            raise NotFound()
        query = OperationQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        products = (
            popular_products(request.auth.staff.unit, point_menu(point))
            .filter(name__icontains=query.validated_data["search"])
            .order_by("name", "id")
        )
        pager = PageNumberPagination()
        return pager.get_paginated_response(
            PublicMenuProductOutput(pager.paginate_queryset(products, request), many=True).data
        )


class StaffOperationView(CookieMutationAPIView):
    permission_classes = [CanViewOperation]

    @extend_schema(parameters=[OperationQuery], responses=page_serializer(OperationSessionOutput))
    def get(self, request):
        query = OperationQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        sessions = (
            ServiceSession.objects.filter(unit=request.auth.staff.unit, status__in=OPEN_STATES)
            .select_related("unit")
            .prefetch_related("point_links__point", "participants")
            .annotate(
                **{
                    f"count_{state.lower()}": Count(
                        "batches__items", filter=Q(batches__items__status=state)
                    )
                    for state in OrderItem.State.values
                }
            )
            .order_by("opened_at", "id")
        )
        if query.validated_data["search"]:
            sessions = sessions.filter(
                id__in=SessionPoint.objects.filter(
                    point__name__icontains=query.validated_data["search"], ended_at__isnull=True
                ).values("session_id")
            )
        pager = PageNumberPagination()
        page = pager.paginate_queryset(sessions, request)
        return pager.get_paginated_response(
            [
                {
                    **session_data(session),
                    "item_counts": {
                        state: getattr(session, f"count_{state.lower()}")
                        for state in OrderItem.State.values
                    },
                }
                for session in page or []
            ]
        )


class StaffDeliveryItemsView(CookieMutationAPIView):
    permission_classes = [CanViewOperation]

    @extend_schema(parameters=[DeliveryQuery], responses=page_serializer(ProductionItemOutput))
    def get(self, request):
        require_permission(
            request.auth,
            "CLAIM_DELIVERY" if request.auth.allows("CLAIM_DELIVERY") else "COMPLETE_DELIVERY",
        )
        query = DeliveryQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        items = work_items(request.auth.staff.unit).filter(status__in=["READY", "DELIVERING"])
        if "status" in query.validated_data:
            items = items.filter(status=query.validated_data["status"])
        if query.validated_data["search"]:
            items = items.filter(
                batch__session__point_links__point__name__icontains=query.validated_data["search"],
                batch__session__point_links__ended_at__isnull=True,
            ).distinct()
        pager = PageNumberPagination()
        page: list[OrderItem] | None = pager.paginate_queryset(items, request)
        return pager.get_paginated_response(ProductionItemOutput(page, many=True).data)


class StaffSessionOrdersView(CookieMutationAPIView):
    permission_classes = [CanViewOperation]

    @extend_schema(responses=page_serializer(BatchOutput))
    def get(self, request, identifier):
        if not ServiceSession.objects.filter(id=identifier, unit=request.auth.staff.unit).exists():
            raise NotFound()
        pager = PageNumberPagination()
        page: list[OrderBatch] | None = pager.paginate_queryset(
            batches({"session_id": identifier}), request
        )
        return pager.get_paginated_response(BatchOutput(page, many=True).data)

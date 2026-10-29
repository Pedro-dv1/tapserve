"""Bounded customer corrections and explicitly authorized staff intervention."""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.access.models import ServicePoint
from apps.access.views import PublicView
from apps.catalog.serializers import PublicProductOutput
from apps.catalog.services import quote
from apps.catalog.views import product_detail
from apps.identity.models import AuditEvent
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from apps.identity.services import rate_limit
from apps.organizations.models import Unit
from common.api import CookieMutationAPIView
from common.idempotency import Conflict, remember, replay

from .models import OrderItem, SelectedOption, ServiceSession, SessionParticipant
from .production import publish
from .serializers import ItemOutput
from .services import OPEN_STATES, require_device


class ItemCommand(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    expected_version = serializers.IntegerField(min_value=1)


class ItemEditInput(ItemCommand):
    fulfillment_mode = serializers.ChoiceField(
        choices=OrderItem.Fulfillment.choices, required=False
    )
    quantity = serializers.IntegerField(min_value=1, max_value=99)
    option_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100)
    notes = serializers.CharField(max_length=500, allow_blank=True)
    participant_id = serializers.UUIDField(allow_null=True, required=False)


class ItemCancelInput(ItemCommand):
    reason = serializers.CharField(max_length=300, allow_blank=True, required=False)


class StaffItemEditInput(ItemEditInput):
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


class StaffItemCancelInput(ItemCommand):
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")


def item_record(item) -> dict:
    return {
        "snapshot": item.snapshot,
        "quantity": item.quantity,
        "unit_price": str(item.unit_price),
        "line_total": str(item.line_total),
        "notes": item.notes,
        "status": item.status,
        "fulfillment_mode": item.fulfillment_mode,
        "sector_id": str(item.sector_id),
        "participant_id": str(item.participant_id) if item.participant_id else None,
        "version": item.version,
    }


def change_item(identity, identifier, data: dict, *, cancel=False, manual=False) -> dict:
    actor = str(identity.staff.id if manual else identity.id)
    rate_limit("item-edit:" + actor, 20, 60)
    return _change_item(identity, identifier, data, cancel=cancel, manual=manual)


@transaction.atomic
def _change_item(identity, identifier, data, *, cancel, manual):
    if manual:
        require_permission(identity, "CANCEL_ORDER" if cancel else "EDIT_ORDER")
        scope = {"batch__session__unit": identity.staff.unit}
        device = None
    else:
        point = (
            ServicePoint.objects.select_for_update(of=("self",))
            .select_related("unit__company")
            .get(id=identity.point_id)
        )
        device = require_device(identity, point)
        scope = {"batch__session_id": device.session_id, "batch__device": device}
    session_id = (
        OrderItem.objects.filter(id=identifier, **scope)
        .values_list("batch__session_id", flat=True)
        .first()
    )
    if session_id is None:
        raise NotFound()
    session = (
        ServiceSession.objects.select_for_update(of=("self",))
        .select_related("unit")
        .get(id=session_id)
    )
    item = (
        OrderItem.objects.select_for_update(of=("self",))
        .select_related("batch__session__unit")
        .get(id=identifier)
    )
    if item.batch.session_id != session.id or session.status not in OPEN_STATES:
        raise Conflict()
    if manual:
        require_permission(identity, "CANCEL_ORDER" if cancel else "EDIT_ORDER")
    actor = str(identity.staff.id if manual else identity.id)
    action = "ITEM_CANCEL" if cancel else "ITEM_EDIT"
    previous = replay(actor, action, str(item.id), data["idempotency_key"], data)
    if previous:
        return previous.response
    if item.status in {"DELIVERED", "CANCELLED", "REJECTED"}:
        raise Conflict("Itens entregues, cancelados ou recusados não podem ser alterados.")
    if item.version != data["expected_version"]:
        raise Conflict()
    if not manual and (
        item.status not in {"NEW", "ACCEPTED"}
        or timezone.now()
        >= item.created_at + timedelta(minutes=session.unit.customer_edit_window_minutes)
    ):
        raise Conflict("Chame um atendente para alterar este item.")
    if not cancel and item.status not in {"NEW", "ACCEPTED"}:
        raise Conflict("Um item em produção pode somente receber cancelamento autorizado.")
    before = item_record(item)
    previous_sector = item.sector_id
    if cancel:
        item.status = "CANCELLED"
    else:
        # Validate association under the session lock; omission preserves existing attribution.
        if "participant_id" in data and data["participant_id"] != item.participant_id:
            participant = None
            if data["participant_id"] is not None:
                participant = SessionParticipant.objects.filter(
                    id=data["participant_id"], session=session, active=True
                ).first()
                if participant is None:
                    raise ValidationError(
                        {"participant_id": "Participante indisponível nesta sessão."}
                    )
            item.participant = participant
        mode = data.get("fulfillment_mode", item.fulfillment_mode)
        if not manual and mode != item.fulfillment_mode and item.status != "NEW":
            raise Conflict("Chame um atendente para mudar a modalidade de um item já aceito.")
        snapshot = quote(
            session.unit,
            {
                "product_id": item.product_id,
                **data,
                "fulfillment_mode": mode if mode != item.fulfillment_mode else "DINE_IN",
            },
            lock=True,
        )
        item.fulfillment_mode = mode
        snapshot["fulfillment_mode"] = mode
        item.quantity = data["quantity"]
        item.notes = data["notes"]
        if {str(value) for value in data["option_ids"]} == {
            choice["id"] for choice in item.snapshot["options"]
        }:
            # Quantity/notes/attribution edits retain the price agreed at order creation.
            item.line_total = item.unit_price * item.quantity
            item.snapshot = {
                **item.snapshot,
                "quantity": item.quantity,
                "line_total": str(item.line_total),
                "fulfillment_mode": mode,
            }
        else:
            item.snapshot = snapshot
            item.unit_price = Decimal(snapshot["unit_price"])
            item.line_total = Decimal(snapshot["line_total"])
            item.sector_id = UUID(snapshot["sector_id"])
            SelectedOption.objects.filter(item=item).delete()
            SelectedOption.objects.bulk_create(
                [
                    SelectedOption(
                        item=item,
                        option_id=choice["id"],
                        name=choice["name"],
                        group_name=choice["group_name"],
                        additional_price=Decimal(choice["additional_price"]),
                    )
                    for choice in snapshot["options"]
                ]
            )
    item.version += 1
    item.save()
    session.version += 1
    session.save(update_fields=["version"])
    AuditEvent.objects.create(
        unit=session.unit,
        staff=identity.staff if manual else None,
        device=device,
        action=action,
        resource_id=str(item.id),
        reason=data.get("reason", ""),
        details={"before": before, "after": item_record(item)},
    )
    publish(session, action, [previous_sector, item.sector_id])
    result = dict(ItemOutput(item, context={"device": device}).data)
    remember(session.unit, actor, action, str(item.id), data["idempotency_key"], data, result, 200)
    return result


class PublicItemView(PublicView):
    @extend_schema(request=ItemEditInput, responses=ItemOutput)
    def patch(self, request, identifier):
        data = ItemEditInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_item(request.auth, identifier, data.validated_data))


class PublicItemCancelView(PublicView):
    @extend_schema(request=ItemCancelInput, responses=ItemOutput)
    def post(self, request, identifier):
        data = ItemCancelInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_item(request.auth, identifier, data.validated_data, cancel=True))


class StaffItemView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=StaffItemEditInput, responses=ItemOutput)
    def patch(self, request, identifier):
        data = StaffItemEditInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(change_item(request.auth, identifier, data.validated_data, manual=True))


class StaffItemCancelView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=StaffItemCancelInput, responses=ItemOutput)
    def post(self, request, identifier):
        data = StaffItemCancelInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            change_item(request.auth, identifier, data.validated_data, cancel=True, manual=True)
        )


class StaffProductChoicesView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=PublicProductOutput)
    def get(self, request, identifier):
        require_permission(
            request.auth,
            "EDIT_ORDER" if request.auth.allows("EDIT_ORDER") else "CREATE_MANUAL_ORDER",
        )
        return Response(product_detail(request.auth.staff.unit, identifier))


class OrderingSettingsInput(StrictSerializer):
    table_takeaway_enabled = serializers.BooleanField(required=False)
    leftover_packaging_enabled = serializers.BooleanField(required=False)
    menu_layout = serializers.ChoiceField(choices=["EDITORIAL", "COMPACT"], required=False)


class OrderPolicyInput(OrderingSettingsInput):
    idempotency_key = serializers.UUIDField()
    expected_window_minutes = serializers.IntegerField(min_value=0, max_value=60)
    customer_edit_window_minutes = serializers.IntegerField(min_value=0, max_value=60)
    reason = serializers.CharField(max_length=300, allow_blank=True, default="")
    expected_settings = OrderingSettingsInput(required=False)


class OrderPolicyOutput(serializers.Serializer):
    customer_edit_window_minutes = serializers.IntegerField()
    table_takeaway_enabled = serializers.BooleanField()
    leftover_packaging_enabled = serializers.BooleanField()
    public_pickup_enabled = serializers.BooleanField()
    menu_layout = serializers.CharField()


def policy_data(unit):
    return {
        "customer_edit_window_minutes": unit.customer_edit_window_minutes,
        "table_takeaway_enabled": unit.table_takeaway_enabled,
        "leftover_packaging_enabled": unit.leftover_packaging_enabled,
        "public_pickup_enabled": False,
        "menu_layout": unit.menu_layout,
    }


@transaction.atomic
def set_policy(identity, data):
    require_permission(identity, "MANAGE_SETTINGS")
    unit = Unit.objects.select_for_update(of=("self",)).get(id=identity.staff.unit_id)
    previous = replay(
        str(identity.staff.id), "ORDER_POLICY", str(unit.id), data["idempotency_key"], data
    )
    if previous:
        return previous.response
    before = policy_data(unit)
    if before["customer_edit_window_minutes"] != data["expected_window_minutes"] or any(
        before[key] != value for key, value in data.get("expected_settings", {}).items()
    ):
        raise Conflict()
    unit.customer_edit_window_minutes = data["customer_edit_window_minutes"]
    for key in OrderingSettingsInput().fields.keys():
        if key in data:
            setattr(unit, key, data[key])
    unit.save(
        update_fields=["customer_edit_window_minutes", *OrderingSettingsInput().fields.keys()]
    )
    result = policy_data(unit)
    AuditEvent.objects.create(
        unit=unit,
        staff=identity.staff,
        action="ORDER_POLICY_UPDATED",
        resource_id=str(unit.id),
        reason=data["reason"],
        details={"before": before, "after": result},
    )
    remember(
        unit,
        str(identity.staff.id),
        "ORDER_POLICY",
        str(unit.id),
        data["idempotency_key"],
        data,
        result,
        200,
    )
    from apps.catalog.services import publish_catalog_change

    publish_catalog_change(unit)
    return result


class OrderPolicyView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=OrderPolicyOutput)
    def get(self, request):
        require_permission(request.auth, "MANAGE_SETTINGS")
        return Response(policy_data(request.auth.staff.unit))

    @extend_schema(request=OrderPolicyInput, responses=OrderPolicyOutput)
    def put(self, request):
        data = OrderPolicyInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(set_policy(request.auth, data.validated_data))

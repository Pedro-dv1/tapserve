from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.access.serializers import PointOutput
from apps.catalog.serializers import QuoteInput
from apps.identity.serializers import StrictSerializer

from .models import OrderBatch, OrderItem, SessionParticipant


class OrderLineInput(QuoteInput):
    expected_unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")
    participant_id = serializers.UUIDField(allow_null=True, default=None)
    participant_name = serializers.CharField(max_length=100, allow_blank=True, default="")

    def validate(self, data):
        if data["participant_id"] is not None and data["participant_name"]:
            raise serializers.ValidationError(
                "Escolha um participante existente ou um nome temporário."
            )
        return data


class OrderInput(StrictSerializer):
    idempotency_key = serializers.UUIDField()
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")
    items = serializers.ListField(child=OrderLineInput(), min_length=1, max_length=50)


class ManualOrderInput(OrderInput):
    point_id = serializers.UUIDField()


class ParticipantInput(StrictSerializer):
    display_name = serializers.CharField(max_length=100)


class ParticipantOutput(serializers.ModelSerializer):
    class Meta:
        model = SessionParticipant
        fields = ["id", "display_name", "active"]


class ItemOutput(serializers.ModelSerializer):
    chargeable_total = serializers.SerializerMethodField()
    participant_name = serializers.CharField(source="participant.display_name", allow_null=True)
    editable_until = serializers.SerializerMethodField()
    can_customer_change = serializers.SerializerMethodField()

    def get_chargeable_total(self, item) -> str:
        return str(Decimal("0.00") if item.status in {"CANCELLED", "REJECTED"} else item.line_total)

    def get_editable_until(self, item) -> str:
        return (
            item.created_at
            + timedelta(minutes=item.batch.session.unit.customer_edit_window_minutes)
        ).isoformat()

    def get_can_customer_change(self, item) -> bool:
        device = self.context.get("device")
        return bool(
            device is not None
            and item.batch.device_id == device.id
            and item.status in {"NEW", "ACCEPTED"}
            and timezone.now()
            < item.created_at
            + timedelta(minutes=item.batch.session.unit.customer_edit_window_minutes)
        )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "version",
            "product_id",
            "editable_until",
            "can_customer_change",
            "snapshot",
            "quantity",
            "notes",
            "status",
            "fulfillment_mode",
            "unit_price",
            "line_total",
            "chargeable_total",
            "participant_id",
            "participant_name",
            "created_at",
            "updated_at",
            "sector_id",
            "delivered_by_id",
        ]


class BatchOutput(serializers.ModelSerializer):
    items = ItemOutput(many=True)
    all_ready = serializers.SerializerMethodField()
    origin = serializers.SerializerMethodField()
    staff_name = serializers.CharField(source="staff.name", allow_null=True)
    point_names = serializers.SerializerMethodField()

    def get_origin(self, batch) -> str:
        return "MANUAL" if batch.staff_id else "CUSTOMER"

    def get_point_names(self, batch) -> list[str]:
        links = list(batch.session.point_links.all())
        current = [link for link in links if link.ended_at is None]
        return [link.point.label for link in current or links]

    def get_all_ready(self, batch) -> bool:
        relevant = [
            item.status
            for item in batch.items.all()
            if item.status not in {"CANCELLED", "REJECTED"}
        ]
        return bool(relevant) and all(
            status in {"READY", "DELIVERING", "DELIVERED"} for status in relevant
        )

    class Meta:
        model = OrderBatch
        fields = [
            "id",
            "session_id",
            "created_at",
            "notes",
            "items",
            "all_ready",
            "origin",
            "channel",
            "staff_name",
            "point_names",
        ]


class OrderReceiptOutput(serializers.Serializer):
    batch = BatchOutput()
    version = serializers.IntegerField()


class SessionOutput(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    opened_at = serializers.DateTimeField()
    version = serializers.IntegerField()
    customer_edit_window_minutes = serializers.IntegerField()
    points = serializers.ListField(child=serializers.DictField())
    participants = ParticipantOutput(many=True)


class PublicSessionContext(serializers.Serializer):
    leftover_packaging_enabled = serializers.BooleanField()
    session = SessionOutput(allow_null=True)
    point_status = serializers.ChoiceField(choices=["FREE", "OCCUPIED"])
    point = PointOutput()

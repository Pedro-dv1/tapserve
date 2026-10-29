import uuid

from django.db import models


class ServiceSession(models.Model):
    class State(models.TextChoices):
        OPEN = "OPEN"
        CHECK_REQUESTED = "CHECK_REQUESTED"
        CLOSING = "CLOSING"
        CLOSED = "CLOSED"
        REOPENED = "REOPENED"
        MERGED = "MERGED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=State.choices, default=State.OPEN)
    opened_at = models.DateTimeField(auto_now_add=True)
    check_requested_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    merged_into = models.ForeignKey("self", null=True, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "OPEN",
                        "CHECK_REQUESTED",
                        "CLOSING",
                        "CLOSED",
                        "REOPENED",
                        "MERGED",
                    ]
                ),
                name="session_status_valid",
            )
        ]
        indexes = [
            models.Index(fields=["unit", "status", "opened_at"], name="session_unit_status_idx")
        ]


class SessionPoint(models.Model):
    session = models.ForeignKey(
        ServiceSession, on_delete=models.PROTECT, related_name="point_links"
    )
    point = models.ForeignKey(
        "access.ServicePoint", on_delete=models.PROTECT, related_name="session_links"
    )
    activated_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["point"],
                condition=models.Q(ended_at__isnull=True),
                name="point_one_live_session",
            )
        ]


class SessionParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ServiceSession, on_delete=models.PROTECT, related_name="participants"
    )
    display_name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "display_name"], name="participant_session_name_unique"
            )
        ]


class OrderBatch(models.Model):
    class Channel(models.TextChoices):
        TABLE = "TABLE"
        STAFF = "STAFF"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ServiceSession, on_delete=models.PROTECT, related_name="batches")
    origin_session = models.ForeignKey(
        ServiceSession, on_delete=models.PROTECT, related_name="original_batches"
    )
    device = models.ForeignKey("access.DeviceAccess", null=True, on_delete=models.PROTECT)
    staff = models.ForeignKey("identity.Staff", null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=500, blank=True)

    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.TABLE)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(channel__in=["TABLE", "STAFF"]), name="batch_channel_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(device__isnull=False, staff__isnull=True)
                | models.Q(device__isnull=True, staff__isnull=False),
                name="batch_exactly_one_actor",
            ),
        ]


class OrderItem(models.Model):
    class Fulfillment(models.TextChoices):
        DINE_IN = "DINE_IN"
        TAKEAWAY = "TAKEAWAY"

    class State(models.TextChoices):
        NEW = "NEW"
        ACCEPTED = "ACCEPTED"
        PREPARING = "PREPARING"
        READY = "READY"
        DELIVERING = "DELIVERING"
        DELIVERED = "DELIVERED"
        CANCELLED = "CANCELLED"
        REJECTED = "REJECTED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(OrderBatch, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    sector = models.ForeignKey("catalog.ProductionSector", on_delete=models.PROTECT)
    participant = models.ForeignKey(SessionParticipant, null=True, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    snapshot = models.JSONField()
    notes = models.CharField(max_length=500, blank=True)
    fulfillment_mode = models.CharField(
        max_length=8, choices=Fulfillment.choices, default=Fulfillment.DINE_IN
    )
    status = models.CharField(max_length=12, choices=State.choices, default=State.NEW)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_by = models.ForeignKey("identity.Staff", null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fulfillment_mode__in=["DINE_IN", "TAKEAWAY"]),
                name="item_fulfillment_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1, quantity__lte=99), name="item_quantity_bounds"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0, line_total__gte=0),
                name="item_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total=models.F("unit_price") * models.F("quantity")),
                name="item_line_total_consistent",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "NEW",
                        "ACCEPTED",
                        "PREPARING",
                        "READY",
                        "DELIVERING",
                        "DELIVERED",
                        "CANCELLED",
                        "REJECTED",
                    ]
                ),
                name="item_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["sector", "status", "created_at"], name="item_sector_status_idx")
        ]


class SelectedOption(models.Model):
    item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="selected_options")
    option = models.ForeignKey("catalog.Option", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    group_name = models.CharField(max_length=100)
    additional_price = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "option"], name="item_option_unique"),
            models.CheckConstraint(
                condition=models.Q(additional_price__gte=0),
                name="selected_option_price_nonnegative",
            ),
        ]


class ProductionAssignment(models.Model):
    staff = models.ForeignKey(
        "identity.Staff", on_delete=models.PROTECT, related_name="production_assignments"
    )
    sector = models.ForeignKey("catalog.ProductionSector", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["staff", "sector"], name="staff_sector_unique")
        ]


class ItemStatusEvent(models.Model):
    item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="status_events")
    staff = models.ForeignKey("identity.Staff", on_delete=models.PROTECT)
    previous_status = models.CharField(max_length=12, choices=OrderItem.State.choices)
    status = models.CharField(max_length=12, choices=OrderItem.State.choices)
    reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DomainEvent(models.Model):
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    session = models.ForeignKey(ServiceSession, null=True, on_delete=models.PROTECT)
    point = models.ForeignKey("access.ServicePoint", null=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=40)
    sector_ids = models.JSONField(default=list)
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(session__isnull=False) | models.Q(point__isnull=False),
                name="event_has_resource",
            )
        ]
        indexes = [models.Index(fields=["unit", "id"], name="event_unit_sequence_idx")]


class ServiceRequest(models.Model):
    class State(models.TextChoices):
        OPEN = "OPEN"
        ASSIGNED = "ASSIGNED"
        RESOLVED = "RESOLVED"
        CANCELLED = "CANCELLED"

    class Kind(models.TextChoices):
        ATTENDANT = "ATTENDANT"
        CHECK = "CHECK"
        CUTLERY = "CUTLERY"
        CLEANING = "CLEANING"
        NAPKIN = "NAPKIN"
        PACKAGING = "PACKAGING"
        OTHER = "OTHER"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    point = models.ForeignKey("access.ServicePoint", on_delete=models.PROTECT)
    session = models.ForeignKey(ServiceSession, null=True, on_delete=models.PROTECT)
    device = models.ForeignKey("access.DeviceAccess", on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    message = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=12, choices=State.choices, default=State.OPEN)
    assigned_to = models.ForeignKey("identity.Staff", null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["point", "kind"],
                condition=models.Q(status__in=["OPEN", "ASSIGNED"]),
                name="request_one_active_kind_per_point",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["OPEN", "ASSIGNED", "RESOLVED", "CANCELLED"]),
                name="request_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    kind__in=[
                        "ATTENDANT",
                        "CUTLERY",
                        "CLEANING",
                        "NAPKIN",
                        "OTHER",
                        "CHECK",
                        "PACKAGING",
                    ]
                ),
                name="request_kind_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(status__in=["ASSIGNED", "RESOLVED"])
                | models.Q(assigned_to__isnull=False),
                name="request_assigned_actor_required",
            ),
        ]
        indexes = [models.Index(fields=["unit", "status", "created_at"], name="request_queue_idx")]


class RealtimeLease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    actor = models.CharField(max_length=44)
    expires_at = models.DateTimeField(db_index=True)
    acknowledged = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["unit", "actor", "expires_at"], name="socket_actor_expiry_idx")
        ]

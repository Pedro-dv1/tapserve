import uuid

from django.db import models


class ServicePoint(models.Model):
    class Kind(models.TextChoices):
        TABLE = "TABLE", "Mesa"
        COUNTER = "COUNTER", "Balcão"
        PICKUP = "PICKUP", "Retirada"
        OTHER = "OTHER", "Outro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    menu = models.ForeignKey(
        "catalog.Menu", null=True, on_delete=models.PROTECT, related_name="service_points"
    )
    number = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=10, choices=Kind.choices)
    active = models.BooleanField(default=True)
    access_enabled = models.BooleanField(default=True)
    nfc_enabled = models.BooleanField(default=True)
    qr_enabled = models.BooleanField(default=True)
    block_new_devices = models.BooleanField(default=False)
    token_digest = models.CharField(max_length=64, unique=True)
    token_ciphertext = models.BinaryField()
    token_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def label(self):
        identifier = (
            f"Mesa {self.number:02d}" if self.type == self.Kind.TABLE and self.number else ""
        )
        name = self.name
        if identifier and name.casefold() in {
            identifier.casefold(),
            f"mesa {self.number}",
            str(self.number),
        }:
            name = ""
        return " · ".join(value for value in [identifier, name] if value)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "number"], name="point_unit_number_unique"),
            models.CheckConstraint(
                condition=~models.Q(type="TABLE") | models.Q(number__isnull=False),
                name="table_number_required",
            ),
            models.CheckConstraint(
                condition=models.Q(number__isnull=True)
                | models.Q(number__gte=1, number__lte=999999),
                name="point_number_bounds",
            ),
        ]


class DeviceAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    point = models.ForeignKey(
        ServicePoint, on_delete=models.PROTECT, related_name="device_accesses"
    )
    token_digest = models.CharField(max_length=64, unique=True)
    # Encrypted recovery for an idempotent exchange bound to a server-side browser nonce.
    token_ciphertext = models.BinaryField()
    browser_digest = models.CharField(max_length=64)
    point_token_version = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)
    session = models.ForeignKey(
        "orders.ServiceSession", null=True, on_delete=models.PROTECT, related_name="device_accesses"
    )

    class Meta:
        indexes = [models.Index(fields=["point", "expires_at"], name="device_point_expiry_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("issued_at")), name="device_positive_ttl"
            )
        ]


class DeviceAdmission(models.Model):
    """A browser request is not a device authorization until staff approves it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    point = models.ForeignKey(ServicePoint, on_delete=models.PROTECT)
    session = models.ForeignKey("orders.ServiceSession", null=True, on_delete=models.PROTECT)
    browser_digest = models.CharField(max_length=64)
    point_token_version = models.PositiveIntegerField()
    status = models.CharField(
        max_length=10,
        choices=[(s, s) for s in ("PENDING", "APPROVED", "REJECTED", "EXPIRED", "REVOKED")],
        default="PENDING",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True)
    decided_by = models.ForeignKey("identity.Staff", null=True, on_delete=models.PROTECT)
    device = models.OneToOneField(DeviceAccess, null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["PENDING", "APPROVED", "REJECTED", "EXPIRED", "REVOKED"]
                ),
                name="admission_status_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="APPROVED") | models.Q(decided_by__isnull=False),
                name="admission_approval_has_actor",
            ),
            models.UniqueConstraint(
                fields=["point", "browser_digest"],
                condition=models.Q(status__in=["PENDING", "APPROVED"]),
                name="admission_browser_one_active",
            ),
        ]
        indexes = [
            models.Index(fields=["point", "status", "expires_at"], name="admission_point_queue_idx")
        ]

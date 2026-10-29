import uuid
from datetime import timedelta

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone


class Permission(models.Model):
    code = models.CharField(max_length=40, primary_key=True)


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT, related_name="roles")
    name = models.CharField(max_length=20)
    suggested_permissions = models.ManyToManyField(Permission, related_name="roles")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "name"], name="role_unit_name_unique")
        ]


class Staff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT, related_name="staff")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="staff_assignments",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="staff")
    name = models.CharField(max_length=100)
    login_code = models.CharField(max_length=32)
    pin_hash = models.CharField(max_length=256)
    active = models.BooleanField(default=True)
    credential_version = models.PositiveIntegerField(default=1)
    deleted_at = models.DateTimeField(null=True, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="staff")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "login_code"], name="staff_unit_login_unique")
        ]


def initial_rate_expiry():
    # Preserve any pre-migration counters for longer than the maximum active window.
    return timezone.now() + timedelta(days=1)


class RateBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window = models.BigIntegerField()
    attempts = models.PositiveIntegerField()
    expires_at = models.DateTimeField(default=initial_rate_expiry, db_index=True)


class IdempotencyRecord(models.Model):
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    actor = models.CharField(max_length=64)
    action = models.CharField(max_length=40)
    resource = models.CharField(max_length=64)
    key = models.UUIDField()
    request_digest = models.CharField(max_length=64)
    response = models.JSONField(encoder=DjangoJSONEncoder)
    status = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "action", "resource", "key"], name="idempotency_scope_key_unique"
            )
        ]


class PlatformOperator(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.PROTECT
    )
    active = models.BooleanField(default=True)


class PlatformAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator = models.ForeignKey(PlatformOperator, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    resource_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(
        "organizations.Unit", on_delete=models.PROTECT, related_name="audit_events"
    )
    staff = models.ForeignKey(
        Staff, null=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    device = models.ForeignKey("access.DeviceAccess", null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=64)
    resource_id = models.CharField(max_length=36, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    details = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(staff__isnull=True) | models.Q(device__isnull=True),
                name="audit_at_most_one_actor",
            )
        ]
        indexes = [models.Index(fields=["unit", "-created_at"], name="audit_unit_time_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit events are append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit events are append-only")

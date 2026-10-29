import uuid

from django.db import models


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Unit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="units")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    active = models.BooleanField(default=True)
    timezone = models.CharField(max_length=60, default="America/Sao_Paulo")
    currency = models.CharField(max_length=3, default="BRL", editable=False)
    customer_edit_window_minutes = models.PositiveSmallIntegerField(default=3)
    logo_key = models.CharField(max_length=255, blank=True, default="", editable=False)
    table_takeaway_enabled = models.BooleanField(default=False)
    leftover_packaging_enabled = models.BooleanField(default=False)
    public_pickup_enabled = models.BooleanField(default=False, editable=False)
    menu_layout = models.CharField(
        max_length=9,
        choices=[("EDITORIAL", "Editorial"), ("COMPACT", "Compacto")],
        default="EDITORIAL",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(menu_layout__in=["EDITORIAL", "COMPACT"]),
                name="unit_menu_layout_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(customer_edit_window_minutes__lte=60),
                name="unit_customer_window_bounds",
            ),
            models.UniqueConstraint(fields=["company", "slug"], name="unit_company_slug_unique"),
        ]

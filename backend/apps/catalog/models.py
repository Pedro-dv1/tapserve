from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Menu(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT, related_name="categories")
    name = models.CharField(max_length=100)
    position = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["menu", "name"], name="category_menu_name_unique")
        ]


class ProductionSector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "name"], name="sector_unit_name_unique")
        ]


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("organizations.Unit", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=1000, blank=True)
    long_description = models.CharField(max_length=4000, blank=True, default="")
    ingredients = models.CharField(max_length=1000, blank=True, default="")
    serving_info = models.CharField(max_length=120, blank=True, default="")
    allergen_info = models.CharField(max_length=500, blank=True, default="")
    featured = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    production_sector = models.ForeignKey(ProductionSector, on_delete=models.PROTECT)
    base_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("99999.99"))],
    )
    image_key = models.CharField(max_length=160, blank=True)
    video_key = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)
    available = models.BooleanField(default=True)

    takeaway_allowed = models.BooleanField(default=True)

    applied_option_groups: models.ManyToManyField[OptionGroup, models.Model] = (
        models.ManyToManyField("OptionGroup", related_name="products", blank=True)
    )
    individual_options: models.ManyToManyField[Option, models.Model] = models.ManyToManyField(
        "Option", related_name="products", blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_price__gte=0), name="product_price_nonnegative"
            )
        ]
        indexes = [
            models.Index(
                fields=["unit", "active", "available"], name="product_unit_availability_idx"
            )
        ]


class OptionGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="option_groups")
    name = models.CharField(max_length=100)
    selection_type = models.CharField(
        max_length=10, choices=[("SINGLE", "Única"), ("MULTIPLE", "Múltipla")]
    )
    required = models.BooleanField(default=False)
    min_choices = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(20)])
    max_choices = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    min_choices__lte=models.F("max_choices"),
                    max_choices__gte=1,
                    max_choices__lte=20,
                ),
                name="group_valid_choice_bounds",
            ),
            models.CheckConstraint(
                condition=~models.Q(selection_type="SINGLE") | models.Q(max_choices=1),
                name="group_single_max_one",
            ),
            models.CheckConstraint(
                condition=models.Q(required=False) | models.Q(min_choices__gte=1),
                name="group_required_min_one",
            ),
            models.CheckConstraint(
                condition=models.Q(selection_type__in=["SINGLE", "MULTIPLE"]),
                name="group_selection_type_valid",
            ),
        ]


class ProductPhoto(models.Model):
    """Additional gallery images; the existing product image remains the cover."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="photos")
    image_key = models.CharField(max_length=160, editable=False)
    alt_text = models.CharField(max_length=200, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "id"]
        indexes = [
            models.Index(fields=["product", "active", "position"], name="photo_product_order_idx")
        ]


class Option(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(OptionGroup, on_delete=models.PROTECT, related_name="options")
    name = models.CharField(max_length=100)
    additional_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("99999.99"))],
    )
    available = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(additional_price__gte=0), name="option_price_nonnegative"
            )
        ]

import hashlib
import json

from rest_framework import serializers

from apps.identity.serializers import StrictSerializer
from apps.orders.models import OrderItem

from .models import Category, Menu, Option, OptionGroup, Product, ProductionSector, ProductPhoto


class ScopedInput(StrictSerializer, serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        for field, scope in (
            ("menu", "unit"),
            ("category", "menu__unit"),
            ("production_sector", "unit"),
            ("product", "unit"),
            ("group", "product__unit"),
        ):
            if field in fields:
                related = fields[field]
                if isinstance(related, serializers.PrimaryKeyRelatedField):
                    queryset = related.get_queryset()
                    if queryset is not None:
                        # DRF's Manager|QuerySet stub incorrectly applies Django's Manager descriptor here.
                        related.queryset = queryset.filter(**{scope: self.context["unit"]})  # type: ignore[arg-type]
        return fields


class MenuInput(ScopedInput):
    class Meta:
        model = Menu
        fields = ["name", "active"]


class CategoryInput(ScopedInput):
    class Meta:
        model = Category
        fields = ["name", "menu", "position", "active"]


class SectorInput(ScopedInput):
    class Meta:
        model = ProductionSector
        fields = ["name", "active"]


class AssociationIds(serializers.ListField):
    def get_value(self, dictionary):
        if hasattr(dictionary, "getlist") and self.field_name in dictionary:
            raw = dictionary[self.field_name]
            if not isinstance(raw, str) or len(raw) > 5000:
                raise serializers.ValidationError("Lista de associações inválida.")
            try:
                return json.loads(raw)
            except ValueError as error:
                raise serializers.ValidationError("Lista de associações inválida.") from error
        return super().get_value(dictionary)


class ProductInput(ScopedInput):
    option_group_ids = AssociationIds(
        child=serializers.UUIDField(), max_length=50, required=False, write_only=True
    )
    individual_option_ids = AssociationIds(
        child=serializers.UUIDField(), max_length=100, required=False, write_only=True
    )
    image = serializers.FileField(required=False, write_only=True)
    remove_image = serializers.BooleanField(default=False, write_only=True)
    video = serializers.FileField(required=False, write_only=True)
    remove_video = serializers.BooleanField(default=False, write_only=True)
    idempotency_key = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "long_description",
            "ingredients",
            "serving_info",
            "allergen_info",
            "featured",
            "category",
            "production_sector",
            "base_price",
            "active",
            "available",
            "takeaway_allowed",
            "image",
            "remove_image",
            "video",
            "remove_video",
            "idempotency_key",
            "option_group_ids",
            "individual_option_ids",
        ]

    def validate(self, data):
        for field, model, scope in (
            ("option_group_ids", OptionGroup, "product__unit"),
            ("individual_option_ids", Option, "group__product__unit"),
        ):
            if field in data:
                ids = data[field]
                if len(ids) != len(set(ids)) or model.objects.filter(
                    id__in=ids, **{scope: self.context["unit"]}
                ).count() != len(ids):
                    raise serializers.ValidationError(
                        {field: "Selecione associações distintas desta unidade."}
                    )
        return data


class GroupInput(ScopedInput):
    def create(self, validated_data):
        group = super().create(validated_data)
        group.products.add(group.product)
        return group

    def update(self, instance, validated_data):
        old = instance.product_id
        group = super().update(instance, validated_data)
        if old != group.product_id:
            group.products.remove(old)
            group.products.add(group.product)
        return group

    class Meta:
        model = OptionGroup
        fields = [
            "name",
            "product",
            "selection_type",
            "required",
            "min_choices",
            "max_choices",
            "active",
        ]

    def validate(self, data):
        def current(key, default):
            return data.get(key, getattr(self.instance, key, default))

        minimum, maximum = current("min_choices", 0), current("max_choices", 1)
        if (
            minimum > maximum
            or (current("selection_type", "SINGLE") == "SINGLE" and maximum != 1)
            or (current("required", False) and minimum < 1)
        ):
            raise serializers.ValidationError("Limites de seleção inválidos.")
        return data


class OptionInput(ScopedInput):
    class Meta:
        model = Option
        fields = ["name", "group", "additional_price", "available", "active"]


class MenuOutput(serializers.ModelSerializer):
    points = serializers.SerializerMethodField()

    def get_points(self, menu) -> list[dict[str, str]]:
        return [{"id": str(point.id), "name": point.name} for point in menu.service_points.all()]

    class Meta:
        model = Menu
        fields = ["id", "name", "active", "points"]


class CategoryOutput(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "menu", "position", "active"]


class SectorOutput(serializers.ModelSerializer):
    class Meta:
        model = ProductionSector
        fields = ["id", "name", "active"]


class ProductOutput(serializers.ModelSerializer):
    option_group_ids: serializers.PrimaryKeyRelatedField[OptionGroup] = (
        serializers.PrimaryKeyRelatedField(
            source="applied_option_groups", many=True, read_only=True
        )
    )
    individual_option_ids: serializers.PrimaryKeyRelatedField[Option] = (
        serializers.PrimaryKeyRelatedField(source="individual_options", many=True, read_only=True)
    )
    has_image = serializers.SerializerMethodField()
    image_version = serializers.SerializerMethodField()
    has_video = serializers.SerializerMethodField()

    def get_has_video(self, product) -> bool:
        return bool(product.video_key)

    def get_has_image(self, product) -> bool:
        return bool(product.image_key)

    def get_image_version(self, product) -> str:
        return (
            hashlib.sha256(product.image_key.encode()).hexdigest()[:16] if product.image_key else ""
        )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "long_description",
            "ingredients",
            "serving_info",
            "allergen_info",
            "featured",
            "category",
            "production_sector",
            "base_price",
            "active",
            "available",
            "takeaway_allowed",
            "has_image",
            "image_version",
            "has_video",
            "option_group_ids",
            "individual_option_ids",
        ]


class GroupOutput(serializers.ModelSerializer):
    product_ids: serializers.PrimaryKeyRelatedField[Product] = serializers.PrimaryKeyRelatedField(
        source="products", many=True, read_only=True
    )

    class Meta:
        model = OptionGroup
        fields = [
            "id",
            "name",
            "product",
            "product_ids",
            "selection_type",
            "required",
            "min_choices",
            "max_choices",
            "active",
        ]


class OptionOutput(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "name", "group", "additional_price", "available", "active"]


class QuoteInput(StrictSerializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)
    option_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100, default=list)
    fulfillment_mode = serializers.ChoiceField(
        choices=OrderItem.Fulfillment.choices, required=False
    )


class QuoteOutput(serializers.Serializer):
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
    quantity = serializers.IntegerField()
    options = serializers.ListField(child=serializers.DictField())


class ImageInput(StrictSerializer):
    image = serializers.FileField(max_length=160)


class PublicGroupOutput(GroupOutput):
    options = OptionOutput(many=True)

    class Meta(GroupOutput.Meta):
        fields = [field for field in GroupOutput.Meta.fields if field != "product_ids"] + [
            "options"
        ]


class PublicMenuProductOutput(ProductOutput):
    ordered_quantity = serializers.IntegerField(read_only=True, default=0)
    most_ordered = serializers.SerializerMethodField()

    def get_most_ordered(self, product) -> bool:
        return str(product.id) == str(
            getattr(product, "_most_ordered_id", self.context.get("most_ordered_id"))
        )

    class Meta(ProductOutput.Meta):
        fields = [
            field
            for field in ProductOutput.Meta.fields
            if field
            not in {
                "option_group_ids",
                "individual_option_ids",
                "long_description",
                "ingredients",
                "serving_info",
                "allergen_info",
            }
        ] + ["ordered_quantity", "most_ordered"]


class PhotoOutput(serializers.ModelSerializer):
    class Meta:
        model = ProductPhoto
        fields = ["id", "alt_text", "position"]


class PublicProductOutput(PublicMenuProductOutput):
    takeaway_enabled = serializers.SerializerMethodField()
    groups = PublicGroupOutput(many=True)
    individual_options = OptionOutput(many=True)
    photos = PhotoOutput(many=True)

    def get_takeaway_enabled(self, product) -> bool:
        return product.unit.table_takeaway_enabled and product.takeaway_allowed

    class Meta(PublicMenuProductOutput.Meta):
        fields = PublicMenuProductOutput.Meta.fields + [
            "groups",
            "individual_options",
            "takeaway_enabled",
            "photos",
            "long_description",
            "ingredients",
            "serving_info",
            "allergen_info",
        ]

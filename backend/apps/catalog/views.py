import hashlib

from django.core.files.storage import default_storage
from django.db import IntegrityError, models, transaction
from django.http import FileResponse, HttpResponseNotModified
from django.utils.http import parse_etags
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.access.serializers import ReasonInput
from apps.access.views import PublicView
from apps.identity.models import AuditEvent
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.serializers import ListQuery, StrictSerializer
from apps.identity.services import rate_limit
from common.api import CookieMutationAPIView, page_serializer

from .models import Category, Menu, Option, OptionGroup, Product, ProductionSector
from .schema import CatalogSchema
from .search import search_catalog
from .serializers import (
    CategoryInput,
    CategoryOutput,
    GroupInput,
    GroupOutput,
    ImageInput,
    MenuInput,
    MenuOutput,
    OptionInput,
    OptionOutput,
    PhotoOutput,
    ProductInput,
    ProductOutput,
    PublicGroupOutput,
    PublicMenuProductOutput,
    PublicProductOutput,
    QuoteInput,
    QuoteOutput,
    SectorInput,
    SectorOutput,
)
from .services import (
    available_products,
    point_menu,
    publish_catalog_change,
    quote,
    save_image,
    write_product,
)

CATALOG = {
    "menus": (Menu, MenuInput, MenuOutput, "unit"),
    "categories": (Category, CategoryInput, CategoryOutput, "menu__unit"),
    "sectors": (ProductionSector, SectorInput, SectorOutput, "unit"),
    "products": (Product, ProductInput, ProductOutput, "unit"),
    "option-groups": (OptionGroup, GroupInput, GroupOutput, "product__unit"),
    "options": (Option, OptionInput, OptionOutput, "group__product__unit"),
}


def validate_upload_count(request):
    for field in request.FILES:
        if field not in {"image", "video"} or len(request.FILES.getlist(field)) != 1:
            raise ValidationError("Envie no máximo uma imagem e um vídeo por produto.")


class CatalogListQuery(ListQuery):
    ids = serializers.ListField(child=serializers.UUIDField(), max_length=100, required=False)
    available = serializers.ChoiceField(choices=["true", "false"], required=False)
    menu = serializers.UUIDField(required=False)


class CanManageMenu(IsActiveStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.auth.allows("MANAGE_MENU")


class CatalogView(CookieMutationAPIView):
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [CanManageMenu]
    kind = ""
    http_method_names = ["get", "post", "head", "options"]
    schema = CatalogSchema()

    def get(self, request, identifier=None):
        model, _, output, scope = CATALOG[self.kind]
        queryset = model._default_manager.filter(**{scope: request.auth.staff.unit}).order_by(
            "name", "id"
        )
        query = CatalogListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        if "ids" in query.validated_data:
            queryset = queryset.filter(id__in=query.validated_data["ids"])
        if self.kind == "menus":
            queryset = queryset.prefetch_related("service_points")
        elif self.kind == "products":
            queryset = queryset.prefetch_related("applied_option_groups", "individual_options")
        elif self.kind == "option-groups":
            queryset = queryset.prefetch_related("products")
        if "menu" in query.validated_data:
            menu = Menu.objects.filter(
                id=query.validated_data["menu"], unit=request.auth.staff.unit
            ).first()
            if menu is None:
                raise NotFound()
            scopes = {
                "categories": "menu",
                "products": "category__menu",
            }
            if self.kind in scopes:
                queryset = queryset.filter(**{scopes[self.kind]: menu})
        if query.validated_data["search"]:
            queryset = search_catalog(queryset, query.validated_data["search"])
        if "active" in query.validated_data:
            queryset = queryset.filter(active=query.validated_data["active"] == "true")
        if "available" in query.validated_data:
            if self.kind not in {"products", "options"}:
                raise ValidationError("Disponibilidade não se aplica a este cadastro.")
            queryset = queryset.filter(available=query.validated_data["available"] == "true")
        if identifier is not None:
            obj = queryset.filter(id=identifier).first()
            if obj is None:
                raise NotFound()
            return Response(output(obj).data)
        pager = PageNumberPagination()
        page: list[models.Model] | None = pager.paginate_queryset(queryset, request)
        return pager.get_paginated_response(output(page, many=True).data)

    def post(self, request):
        model, input_class, output, scope = CATALOG[self.kind]
        data = input_class(data=request.data, context={"unit": request.auth.staff.unit})
        data.is_valid(raise_exception=True)
        if self.kind == "products":
            validate_upload_count(request)
            return Response(write_product(request.auth, data), status=201)
        try:
            with transaction.atomic():
                require_permission(request.auth, "MANAGE_MENU")
                obj = data.save(**({"unit": request.auth.staff.unit} if scope == "unit" else {}))
                publish_catalog_change(request.auth.staff.unit)
                AuditEvent.objects.create(
                    unit=request.auth.staff.unit,
                    staff=request.auth.staff,
                    action="CATALOG_CREATED",
                    resource_id=str(obj.pk),
                    reason=self.kind,
                )
        except IntegrityError as error:
            raise ValidationError("Cadastro viola uma regra de integridade.") from error
        return Response(output(obj).data, status=201)

    def patch(self, request, identifier):
        model, input_class, output, scope = CATALOG[self.kind]
        if self.kind == "products":
            product = Product.objects.filter(id=identifier, unit=request.auth.staff.unit).first()
            if product is None:
                raise NotFound()
            product_data = ProductInput(
                product, data=request.data, partial=True, context={"unit": request.auth.staff.unit}
            )
            product_data.is_valid(raise_exception=True)
            validate_upload_count(request)
            return Response(write_product(request.auth, product_data, identifier))
        try:
            with transaction.atomic():
                obj = (
                    model._default_manager.select_for_update(of=("self",))
                    .filter(id=identifier, **{scope: request.auth.staff.unit})
                    .first()
                )
                if obj is None:
                    raise NotFound()
                require_permission(request.auth, "MANAGE_MENU")
                data = input_class(
                    obj, data=request.data, partial=True, context={"unit": request.auth.staff.unit}
                )
                data.is_valid(raise_exception=True)
                obj = data.save()
                publish_catalog_change(request.auth.staff.unit)
                AuditEvent.objects.create(
                    unit=request.auth.staff.unit,
                    staff=request.auth.staff,
                    action="CATALOG_UPDATED",
                    resource_id=str(obj.pk),
                    reason=self.kind,
                )
        except IntegrityError as error:
            raise ValidationError("Cadastro viola uma regra de integridade.") from error
        return Response(output(obj).data)

    def delete(self, request, identifier):
        model, _, _, scope = CATALOG[self.kind]
        data = ReasonInput(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            require_permission(request.auth, "MANAGE_MENU")
            obj = (
                model._default_manager.select_for_update(of=("self",))
                .filter(id=identifier, **{scope: request.auth.staff.unit})
                .first()
            )
            if obj is None:
                raise NotFound()
            model._default_manager.filter(pk=obj.pk).update(active=False)
            publish_catalog_change(request.auth.staff.unit)
            AuditEvent.objects.create(
                unit=request.auth.staff.unit,
                staff=request.auth.staff,
                action="CATALOG_DEACTIVATED",
                resource_id=str(obj.pk),
                reason=data.validated_data["reason"],
            )
        return Response(status=204)


class CatalogDetailView(CatalogView):
    http_method_names = ["get", "patch", "delete", "head", "options"]


def popular_products(unit, menu=None):
    from apps.orders.models import OrderItem

    totals = (
        OrderItem.objects.filter(product_id=models.OuterRef("pk"), batch__session__unit=unit)
        .exclude(status__in=["CANCELLED", "REJECTED"])
        .values("product_id")
        .annotate(total=models.Sum("quantity"))
        .values("total")
    )
    return available_products(unit, menu).annotate(
        ordered_quantity=models.functions.Coalesce(
            models.Subquery(totals, output_field=models.IntegerField()), 0
        )
    )


def most_ordered_id(unit, menu=None):
    return (
        popular_products(unit, menu)
        .filter(ordered_quantity__gt=0)
        .order_by("-ordered_quantity", "id")
        .values_list("id", flat=True)
        .first()
    )


class PublicMenuQuery(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    search = serializers.CharField(max_length=100, allow_blank=True, default="")
    category = serializers.UUIDField(required=False)
    popular = serializers.ChoiceField(choices=["true", "false"], default="false")


class MenuPresentationOutput(serializers.Serializer):
    layout = serializers.ChoiceField(choices=["EDITORIAL", "COMPACT"])
    hero = PublicMenuProductOutput(allow_null=True)
    popular = PublicMenuProductOutput(many=True)


class PublicMenuPage(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = PublicMenuProductOutput(many=True)
    presentation = MenuPresentationOutput()


class PublicMenuView(PublicView):
    @extend_schema(parameters=[PublicMenuQuery], responses=PublicMenuPage)
    def get(self, request):
        unit = request.auth.point.unit
        menu = point_menu(request.auth.point)
        products = (
            popular_products(unit, menu)
            .annotate(
                _most_ordered_id=models.Subquery(
                    popular_products(unit, menu)
                    .filter(ordered_quantity__gt=0)
                    .order_by("-ordered_quantity", "id")
                    .values("id")[:1]
                )
            )
            .order_by("category__position", "category_id", "name", "id")
        )
        query = PublicMenuQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        if data["popular"] == "true":
            products = products.filter(ordered_quantity__gt=0).order_by(
                "-ordered_quantity", "name", "id"
            )
        if data["search"]:
            products = search_catalog(products, data["search"], description=True)
        if "category" in data:
            products = products.filter(category_id=data["category"])
        pager = PageNumberPagination()
        page: list[Product] | None = pager.paginate_queryset(products, request)
        response = pager.get_paginated_response(PublicMenuProductOutput(page, many=True).data)
        hero = (
            products.filter(featured=True).exclude(image_key="").first()
            if not data["search"]
            and "category" not in data
            and data["popular"] == "false"
            and data["page"] == 1
            else None
        )
        response.data["presentation"] = {
            "layout": unit.menu_layout,
            "hero": PublicMenuProductOutput(hero).data if hero else None,
            "popular": PublicMenuProductOutput(
                products.filter(ordered_quantity__gt=0)
                .exclude(image_key="")
                .order_by("-ordered_quantity", "name", "id")[:3]
                if not data["search"] and "category" not in data and data["page"] == 1
                else [],
                many=True,
            ).data,
        }
        return response


class PublicCategoriesView(PublicView):
    @extend_schema(responses=page_serializer(CategoryOutput))
    def get(self, request):
        pager = PageNumberPagination()
        page = pager.paginate_queryset(
            Category.objects.filter(menu=point_menu(request.auth.point), active=True).order_by(
                "position", "name", "id"
            ),
            request,
        )
        return pager.get_paginated_response(CategoryOutput(page, many=True).data)


def product_detail(unit, identifier, menu=None):
    product = popular_products(unit, menu).filter(id=identifier).first()
    if product is None:
        raise NotFound()
    groups = (
        OptionGroup.objects.filter(products=product, active=True)
        .prefetch_related("options")
        .order_by("name", "id")
    )
    result = dict(
        PublicMenuProductOutput(
            product, context={"most_ordered_id": str(most_ordered_id(unit, menu))}
        ).data
    )
    result["groups"] = [
        {
            **PublicGroupOutput(group).data,
            "options": OptionOutput(
                [option for option in group.options.all() if option.active and option.available],
                many=True,
            ).data,
        }
        for group in groups
    ]
    grouped_ids = [group.id for group in groups]
    result["individual_options"] = OptionOutput(
        product.individual_options.filter(active=True, available=True)
        .exclude(group_id__in=grouped_ids)
        .order_by("name", "id"),
        many=True,
    ).data
    result["takeaway_enabled"] = unit.table_takeaway_enabled and product.takeaway_allowed
    result["photos"] = PhotoOutput(product.photos.filter(active=True), many=True).data
    for field in ("long_description", "ingredients", "serving_info", "allergen_info"):
        result[field] = getattr(product, field)
    return result


class PublicProductView(PublicView):
    @extend_schema(responses=PublicProductOutput)
    def get(self, request, identifier):
        return Response(
            product_detail(request.auth.point.unit, identifier, point_menu(request.auth.point))
        )


class PublicQuoteView(PublicView):
    @extend_schema(request=QuoteInput, responses=QuoteOutput)
    def post(self, request):
        rate_limit("quote-device:" + str(request.auth.id), 60, 60)
        data = QuoteInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            quote(request.auth.point.unit, data.validated_data, menu=point_menu(request.auth.point))
        )


class ProductImageView(CookieMutationAPIView):
    permission_classes = [CanManageMenu]
    parser_classes = [MultiPartParser]

    @extend_schema(request=ImageInput, responses=ProductOutput)
    def post(self, request, identifier):
        if sum(len(request.FILES.getlist(field)) for field in request.FILES) != 1:
            raise ValidationError("Envie uma única imagem.")
        data = ImageInput(data=request.data)
        data.is_valid(raise_exception=True)
        rate_limit("image-staff:" + str(request.auth.staff.id), 20, 60)
        return Response(
            ProductOutput(save_image(request.auth, identifier, data.validated_data["image"])).data
        )

    @extend_schema(responses={(200, "image/webp"): bytes})
    def get(self, request, identifier):
        product = Product.objects.filter(unit=request.auth.staff.unit, id=identifier).first()
        return image_response(request, product)


def image_response(request, product):
    if product is None or not product.image_key:
        raise NotFound()
    etag = '"' + hashlib.sha256(product.image_key.encode()).hexdigest() + '"'
    response: FileResponse | HttpResponseNotModified
    if etag in parse_etags(request.headers.get("If-None-Match", "")):
        response = HttpResponseNotModified()
    else:
        try:
            file = default_storage.open(product.image_key, "rb")
        except FileNotFoundError as error:
            raise NotFound() from error
        response = FileResponse(
            file, content_type="image/webp", filename="product.webp", as_attachment=False
        )
    # Authorization and availability run on every revalidation, including 304 responses.
    response["Cache-Control"] = "private, no-cache"
    response["ETag"] = etag
    response["Vary"] = "Cookie"
    return response


class PublicProductImageView(PublicView):
    @extend_schema(responses={(200, "image/webp"): bytes})
    def get(self, request, identifier):
        return image_response(
            request,
            available_products(request.auth.point.unit, point_menu(request.auth.point))
            .filter(id=identifier)
            .first(),
        )


class ProductVideoView(CookieMutationAPIView):
    permission_classes = [CanManageMenu]

    @extend_schema(
        responses={
            (200, "video/mp4"): bytes,
            (206, "video/mp4"): bytes,
            (200, "video/webm"): bytes,
            (206, "video/webm"): bytes,
        }
    )
    def get(self, request, identifier):
        from .video import video_response

        return video_response(
            request, Product.objects.filter(unit=request.auth.staff.unit, id=identifier).first()
        )


class PublicProductVideoView(PublicView):
    @extend_schema(
        responses={
            (200, "video/mp4"): bytes,
            (206, "video/mp4"): bytes,
            (200, "video/webm"): bytes,
            (206, "video/webm"): bytes,
        }
    )
    def get(self, request, identifier):
        from .video import video_response

        return video_response(
            request,
            available_products(request.auth.point.unit, point_menu(request.auth.point))
            .filter(id=identifier)
            .first(),
        )

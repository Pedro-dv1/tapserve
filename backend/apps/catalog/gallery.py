"""Bounded additional images, using the catalog's existing validation and storage."""

import hashlib
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.access.views import PublicView
from apps.identity.models import AuditEvent
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.serializers import StrictSerializer
from apps.identity.services import rate_limit
from common.api import CookieMutationAPIView
from common.idempotency import remember, replay

from .models import Product, ProductPhoto
from .serializers import PhotoOutput
from .services import (
    available_products,
    delete_image,
    normalize_image,
    point_menu,
    publish_catalog_change,
)
from .views import image_response


class PhotoMetadataInput(StrictSerializer):
    alt_text = serializers.CharField(max_length=200, allow_blank=True, required=False)
    position = serializers.IntegerField(min_value=0, max_value=32767, required=False)


class PhotoUploadInput(PhotoMetadataInput):
    idempotency_key = serializers.UUIDField()
    image = serializers.FileField()


class ProductPhotosView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]
    parser_classes = [JSONParser, MultiPartParser]

    @extend_schema(responses=PhotoOutput(many=True))
    def get(self, request, identifier):
        require_permission(request.auth, "MANAGE_MENU")
        if not Product.objects.filter(id=identifier, unit=request.auth.staff.unit).exists():
            raise NotFound()
        return Response(
            PhotoOutput(
                ProductPhoto.objects.filter(product_id=identifier, active=True), many=True
            ).data
        )

    @extend_schema(request=PhotoUploadInput, responses={201: PhotoOutput})
    def post(self, request, identifier):
        require_permission(request.auth, "MANAGE_MENU")
        if not Product.objects.filter(id=identifier, unit=request.auth.staff.unit).exists():
            raise NotFound()
        rate_limit("gallery-staff:" + str(request.auth.staff.id), 20, 60)
        data = PhotoUploadInput(data=request.data)
        data.is_valid(raise_exception=True)
        if set(request.FILES) != {"image"} or len(request.FILES.getlist("image")) != 1:
            raise ValidationError("Envie somente uma imagem por vez.")
        normalized = normalize_image(data.validated_data["image"])
        body = {key: value for key, value in data.validated_data.items() if key != "image"}
        body["image_digest"] = hashlib.sha256(normalized).hexdigest()
        stored = None
        try:
            with transaction.atomic():
                require_permission(request.auth, "MANAGE_MENU")
                product = Product.objects.select_for_update().get(
                    id=identifier, unit=request.auth.staff.unit
                )
                previous = replay(
                    str(request.auth.staff.id),
                    "PRODUCT_PHOTO",
                    str(identifier),
                    body["idempotency_key"],
                    body,
                )
                if previous:
                    return Response(previous.response, status=previous.status)
                if product.photos.filter(active=True).count() >= 6:
                    raise ValidationError(
                        "A galeria permite até seis fotos adicionais por produto."
                    )
                stored = default_storage.save(
                    f"products/{product.unit_id}/{uuid.uuid4()}.webp", ContentFile(normalized)
                )
                photo = ProductPhoto.objects.create(
                    product=product,
                    image_key=stored,
                    alt_text=body.get("alt_text", ""),
                    position=body.get("position", 0),
                )
                result = dict(PhotoOutput(photo).data)
                AuditEvent.objects.create(
                    unit=product.unit,
                    staff=request.auth.staff,
                    action="PRODUCT_PHOTO_ADDED",
                    resource_id=str(photo.id),
                    details={"product_id": str(product.id), **result},
                )
                publish_catalog_change(product.unit)
                remember(
                    product.unit,
                    str(request.auth.staff.id),
                    "PRODUCT_PHOTO",
                    str(identifier),
                    body["idempotency_key"],
                    body,
                    result,
                    201,
                )
            return Response(result, status=201)
        except Exception:
            if stored:
                delete_image(stored)
            raise


class ProductPhotoView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses={(200, "image/webp"): bytes})
    def get(self, request, identifier, photo_id):
        require_permission(request.auth, "MANAGE_MENU")
        return image_response(
            request,
            ProductPhoto.objects.filter(
                id=photo_id,
                product_id=identifier,
                product__unit=request.auth.staff.unit,
                active=True,
            ).first(),
        )

    @extend_schema(request=PhotoMetadataInput, responses=PhotoOutput)
    @transaction.atomic
    def patch(self, request, identifier, photo_id):
        require_permission(request.auth, "MANAGE_MENU")
        photo = (
            ProductPhoto.objects.select_for_update()
            .filter(
                id=photo_id,
                product_id=identifier,
                product__unit=request.auth.staff.unit,
                active=True,
            )
            .first()
        )
        if photo is None:
            raise NotFound()
        data = PhotoMetadataInput(data=request.data)
        data.is_valid(raise_exception=True)
        before = dict(PhotoOutput(photo).data)
        for field, value in data.validated_data.items():
            setattr(photo, field, value)
        photo.save(update_fields=list(data.validated_data))
        result = dict(PhotoOutput(photo).data)
        AuditEvent.objects.create(
            unit=request.auth.staff.unit,
            staff=request.auth.staff,
            action="PRODUCT_PHOTO_UPDATED",
            resource_id=str(photo.id),
            details={"before": before, "after": result},
        )
        publish_catalog_change(request.auth.staff.unit)
        return Response(result)

    @extend_schema(request=None, responses={204: None})
    @transaction.atomic
    def delete(self, request, identifier, photo_id):
        require_permission(request.auth, "MANAGE_MENU")
        photo = (
            ProductPhoto.objects.select_for_update()
            .filter(
                id=photo_id,
                product_id=identifier,
                product__unit=request.auth.staff.unit,
                active=True,
            )
            .first()
        )
        if photo is None:
            raise NotFound()
        photo.active = False
        photo.save(update_fields=["active"])
        AuditEvent.objects.create(
            unit=request.auth.staff.unit,
            staff=request.auth.staff,
            action="PRODUCT_PHOTO_REMOVED",
            resource_id=str(photo.id),
        )
        publish_catalog_change(request.auth.staff.unit)
        transaction.on_commit(lambda: delete_image(photo.image_key), robust=True)
        return Response(status=204)


class PublicProductPhotoView(PublicView):
    @extend_schema(responses={(200, "image/webp"): bytes})
    def get(self, request, identifier, photo_id):
        product = (
            available_products(request.auth.point.unit, point_menu(request.auth.point))
            .filter(id=identifier)
            .first()
        )
        if product is None:
            raise NotFound()
        return image_response(request, product.photos.filter(id=photo_id, active=True).first())

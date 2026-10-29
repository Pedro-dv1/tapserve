from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.catalog.serializers import ImageInput
from apps.identity.permissions import IsActiveStaff, require_permission
from apps.identity.services import rate_limit
from common.api import CookieMutationAPIView

from .services import logo_response, logo_url, set_logo


class UnitLogoOutput(serializers.Serializer):
    logo_url = serializers.CharField(allow_null=True)
    max_bytes = serializers.IntegerField()


def logo_data(unit):
    return {"logo_url": logo_url(unit, "admin"), "max_bytes": settings.PRODUCT_IMAGE_MAX_BYTES}


class UnitLogoView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]
    parser_classes = [MultiPartParser]

    @extend_schema(responses=UnitLogoOutput)
    def get(self, request):
        require_permission(request.auth, "MANAGE_SETTINGS")
        return Response(logo_data(request.auth.staff.unit))

    @extend_schema(request=ImageInput, responses=UnitLogoOutput)
    def put(self, request):
        require_permission(request.auth, "MANAGE_SETTINGS")
        rate_limit("logo-staff:" + str(request.auth.staff.id), 20, 60)
        if set(request.FILES) != {"image"} or len(request.FILES.getlist("image")) != 1:
            raise ValidationError("Envie uma única imagem.")
        data = ImageInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(logo_data(set_logo(request.auth, data.validated_data["image"])))

    @extend_schema(responses=UnitLogoOutput)
    def delete(self, request):
        require_permission(request.auth, "MANAGE_SETTINGS")
        return Response(logo_data(set_logo(request.auth)))


class UnitLogoImageView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses={(200, "image/webp"): bytes})
    def get(self, request):
        require_permission(request.auth, "MANAGE_SETTINGS")
        return logo_response(request.auth.staff.unit)

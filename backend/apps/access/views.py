from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from apps.catalog.models import Menu
from apps.catalog.serializers import MenuOutput
from apps.identity.permissions import IsActiveStaff
from apps.identity.serializers import ListQuery
from apps.organizations.services import logo_response, logo_url
from common.api import CookieMutationAPIView, page_serializer

from .models import DeviceAccess, ServicePoint
from .serializers import (
    AccessInput,
    DeviceOutput,
    IdentifierInput,
    PointInput,
    PointOutput,
    PointUpdateInput,
    PointUrlOutput,
    PresenceOutput,
    PublicContextOutput,
    ReasonInput,
)
from .services import (
    active_device,
    change_point,
    configure_identifier,
    connected_devices,
    create_point,
    exchange,
    point_url,
    revoke_device,
)


class CanManagePoints(IsActiveStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.auth.allows(
            "MANAGE_SERVICE_POINTS"
        )


class PointListView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(parameters=[ListQuery], responses=page_serializer(PointOutput))
    def get(self, request):
        query = ListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        points = ServicePoint.objects.filter(unit=request.auth.staff.unit).order_by("name", "id")
        if query.validated_data["search"]:
            points = points.filter(name__icontains=query.validated_data["search"])
        if "active" in query.validated_data:
            points = points.filter(active=query.validated_data["active"] == "true")
        pager = PageNumberPagination()
        page = pager.paginate_queryset(points, request)
        return pager.get_paginated_response(PointOutput(page, many=True).data)

    @extend_schema(request=PointInput, responses={201: PointOutput})
    def post(self, request):
        serializer = PointInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(create_point(request.auth, serializer.validated_data), status=201)


class PointMenuOptionsView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(
        responses=page_serializer(MenuOutput), operation_id="admin_point_menu_options_list"
    )
    def get(self, request, identifier=None):
        query = ListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        menus = (
            Menu.objects.filter(unit=request.auth.staff.unit)
            .prefetch_related("service_points")
            .order_by("name", "id")
        )
        if identifier:
            menu = menus.filter(id=identifier).first()
            if menu is None:
                raise NotFound()
            return Response(MenuOutput(menu).data)
        menus = menus.filter(active=True, name__icontains=query.validated_data["search"])
        pager = PageNumberPagination()
        page = pager.paginate_queryset(menus, request)
        return pager.get_paginated_response(MenuOutput(page, many=True).data)


class PointMenuOptionDetailView(PointMenuOptionsView):
    @extend_schema(responses=MenuOutput, operation_id="admin_point_menu_options_retrieve")
    def get(self, request, identifier=None):
        return super().get(request, identifier)


class PointDetailView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(request=PointUpdateInput, responses=PointOutput)
    def patch(self, request, identifier):
        data = PointUpdateInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            PointOutput(change_point(request.auth, identifier, data.validated_data)).data
        )


class PointUrlView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(responses=PointUrlOutput)
    def get(self, request, identifier):
        point = ServicePoint.objects.filter(id=identifier, unit=request.auth.staff.unit).first()
        if point is None:
            raise NotFound()
        return Response({"url": point_url(point)})


class PointQrView(PointUrlView):
    @extend_schema(responses={(200, "image/svg+xml"): bytes})
    def get(self, request, identifier):
        import qrcode
        from qrcode.image.svg import SvgPathFillImage

        point = ServicePoint.objects.filter(
            id=identifier, unit=request.auth.staff.unit, qr_enabled=True
        ).first()
        if point is None:
            raise NotFound()
        svg = qrcode.make(point_url(point), image_factory=SvgPathFillImage).to_string()
        response = HttpResponse(svg, content_type="image/svg+xml")
        response["Content-Disposition"] = f'attachment; filename="tapserve-point-{point.id}.svg"'
        return response


class PointIdentifierView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(request=IdentifierInput, responses=PointOutput)
    def post(self, request, identifier):
        data = IdentifierInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            PointOutput(configure_identifier(request.auth, identifier, data.validated_data)).data
        )


class PointPresenceView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(responses=PresenceOutput)
    def get(self, request, identifier):
        point = ServicePoint.objects.filter(id=identifier, unit=request.auth.staff.unit).first()
        if point is None:
            raise NotFound()
        return Response(
            {"connected_devices": connected_devices(point).count(), "timeout_seconds": 30}
        )


class PointDevicesView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(responses=page_serializer(DeviceOutput))
    def get(self, request, identifier):
        point = ServicePoint.objects.filter(id=identifier, unit=request.auth.staff.unit).first()
        if point is None:
            raise NotFound()
        pager = PageNumberPagination()
        page = pager.paginate_queryset(
            DeviceAccess.objects.filter(point=point).order_by("-issued_at", "id"), request
        )
        return pager.get_paginated_response(DeviceOutput(page, many=True).data)


class DeviceRevokeView(CookieMutationAPIView):
    permission_classes = [CanManagePoints]

    @extend_schema(request=ReasonInput, responses={204: None})
    def post(self, request, identifier):
        data = ReasonInput(data=request.data)
        data.is_valid(raise_exception=True)
        revoke_device(request.auth, identifier, data.validated_data["reason"])
        return Response(status=204)


def public_context(device):
    return {
        "device_id": str(device.id),
        "point": PointOutput(device.point).data,
        "company_name": device.point.unit.company.name,
        "unit_name": device.point.unit.name,
        "unit_timezone": device.point.unit.timezone,
        "leftover_packaging_enabled": device.point.unit.leftover_packaging_enabled,
        "unit_logo_url": logo_url(device.point.unit),
        "expires_at": device.expires_at,
    }


class AccessView(CookieMutationAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=AccessInput, responses=PublicContextOutput, auth=[])
    def post(self, request):
        if settings.AUTHENTICATION_REQUIRE_HTTPS and not request.is_secure():
            raise PermissionDenied()
        data = AccessInput(data=request.data)
        data.is_valid(raise_exception=True)
        device, token = exchange(request._request, data.validated_data["public_token"])
        response = Response(public_context(device))
        response.set_cookie(
            settings.DEVICE_COOKIE_NAME,
            token,
            max_age=max(0, int((device.expires_at - timezone.now()).total_seconds())),
            path="/",
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite="Lax",
        )
        return response


class DeviceAuthentication(BaseAuthentication):
    def authenticate(self, request):
        device = active_device(request.COOKIES.get(settings.DEVICE_COOKIE_NAME))
        if device is None:
            return None
        now = timezone.now()
        if device.last_seen_at is None or device.last_seen_at <= now - timedelta(seconds=30):
            # HTTP fallback traffic prevents an active browser from losing an idle slot.
            DeviceAccess.objects.filter(id=device.id).update(last_seen_at=now)
            device.last_seen_at = now
        from django.contrib.auth.models import AnonymousUser

        return AnonymousUser(), device

    def authenticate_header(self, request):
        return "Device"


class HasDeviceAccess(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, DeviceAccess)


class PublicView(CookieMutationAPIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [HasDeviceAccess]


class PublicContextView(PublicView):
    @extend_schema(responses=PublicContextOutput)
    def get(self, request):
        return Response(public_context(request.auth))


class PublicUnitLogoView(PublicView):
    @extend_schema(responses={(200, "image/webp"): bytes})
    def get(self, request):
        return logo_response(request.auth.point.unit)

from django.conf import settings
from django.contrib.auth import logout
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.access.serializers import ReasonInput
from common.api import CookieMutationAPIView, page_serializer

from .authentication import StaffIdentity
from .models import AuditEvent, Role, Staff
from .permissions import CanManageStaff, IsActiveStaff, require_permission
from .serializers import (
    ContextOutput,
    ListQuery,
    PasswordLoginInput,
    PinLoginInput,
    RoleOutput,
    StaffInput,
    StaffOutput,
    StaffUpdateInput,
    StrictSerializer,
    UnitMembershipOutput,
    UnitSelectionInput,
)
from .services import authenticate_staff, create_staff, delete_staff, update_staff


def context_data(staff: Staff, strong: bool) -> dict:
    return {
        "staff": StaffOutput(staff).data,
        "company_name": staff.unit.company.name,
        "unit_id": str(staff.unit_id),
        "unit_name": staff.unit.name,
        "auth_strength": "password" if strong else "pin",
    }


class PinLoginView(CookieMutationAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=PinLoginInput, responses=ContextOutput, auth=[])
    def post(self, request):
        if settings.AUTHENTICATION_REQUIRE_HTTPS and not request.is_secure():
            raise PermissionDenied()
        serializer = PinLoginInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = authenticate_staff(request._request, serializer.validated_data, strong=False)
        return Response(context_data(staff, False))


class PasswordLoginView(CookieMutationAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=PasswordLoginInput, responses=ContextOutput, auth=[])
    def post(self, request):
        if settings.AUTHENTICATION_REQUIRE_HTTPS and not request.is_secure():
            raise PermissionDenied()
        serializer = PasswordLoginInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = authenticate_staff(request._request, serializer.validated_data, strong=True)
        return Response(context_data(staff, True))


class StaffMeView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(responses=ContextOutput)
    def get(self, request):
        identity: StaffIdentity = request.auth
        return Response(context_data(identity.staff, identity.strong))


class StaffUnitsView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    def memberships(self, request):
        require_permission(request.auth, "MANAGE_MENU")
        if not request.auth.strong:
            raise PermissionDenied()
        return (
            Staff.objects.filter(
                user=request.user,
                active=True,
                unit__active=True,
                unit__company=request.auth.staff.unit.company,
                unit__company__active=True,
                permissions__code="MANAGE_MENU",
            )
            .select_related("unit")
            .order_by("unit__name", "id")
        )

    @extend_schema(parameters=[ListQuery], responses=page_serializer(UnitMembershipOutput))
    def get(self, request):
        query = ListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        memberships = self.memberships(request).filter(
            unit__name__icontains=query.validated_data["search"]
        )
        pager = PageNumberPagination()
        page: list[Staff] | None = pager.paginate_queryset(memberships, request)
        return pager.get_paginated_response(UnitMembershipOutput(page, many=True).data)

    @extend_schema(request=UnitSelectionInput, responses=ContextOutput)
    def post(self, request):
        data = UnitSelectionInput(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            staff = (
                self.memberships(request)
                .select_for_update(of=("self",))
                .filter(id=data.validated_data["membership_id"])
                .first()
            )
            if staff is None:
                raise NotFound()
            AuditEvent.objects.create(
                unit=staff.unit,
                staff=staff,
                action="STAFF_UNIT_SELECTED",
                details={"previous_unit_id": str(request.auth.staff.unit_id)},
            )
        # Rotating invalidates the previous cookie, including its open WebSockets.
        request.session.cycle_key()
        request.session.update(
            {
                "tapserve_staff_id": str(staff.id),
                "tapserve_credential_version": staff.credential_version,
            }
        )
        return Response(context_data(staff, True))


class LogoutView(CookieMutationAPIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(request=StrictSerializer, responses={204: None})
    def post(self, request):
        serializer = StrictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identity: StaffIdentity = request.auth
        with transaction.atomic():
            AuditEvent.objects.create(
                unit=identity.staff.unit, staff=identity.staff, action="STAFF_LOGOUT"
            )
            logout(request._request)
        return Response(status=204)


class StaffListView(CookieMutationAPIView):
    permission_classes = [CanManageStaff]

    @extend_schema(
        operation_id="admin_staff_list",
        parameters=[ListQuery],
        responses=page_serializer(StaffOutput),
    )
    def get(self, request):
        query = ListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        queryset = (
            Staff.objects.filter(unit=request.auth.staff.unit, deleted_at__isnull=True)
            .select_related("role")
            .prefetch_related("permissions")
            .order_by("name", "id")
        )
        if query.validated_data["search"]:
            queryset = queryset.filter(name__icontains=query.validated_data["search"])
        if "active" in query.validated_data:
            queryset = queryset.filter(active=query.validated_data["active"] == "true")
        pagination = PageNumberPagination()
        return pagination.get_paginated_response(
            StaffOutput(pagination.paginate_queryset(queryset, request), many=True).data
        )

    @extend_schema(request=StaffInput, responses={201: StaffOutput})
    def post(self, request):
        serializer = StaffInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = create_staff(request.auth, serializer.validated_data)
        return Response(StaffOutput(staff).data, status=201)


class StaffDetailView(CookieMutationAPIView):
    permission_classes = [CanManageStaff]

    @extend_schema(responses=StaffOutput)
    def get(self, request, identifier):
        staff = (
            Staff.objects.filter(
                id=identifier, unit=request.auth.staff.unit, deleted_at__isnull=True
            )
            .select_related("role")
            .prefetch_related("permissions")
            .first()
        )
        if staff is None:
            raise NotFound()
        return Response(StaffOutput(staff).data)

    @extend_schema(request=StaffUpdateInput, responses=StaffOutput)
    def patch(self, request, identifier):
        serializer = StaffUpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            StaffOutput(update_staff(request.auth, identifier, serializer.validated_data)).data
        )

    @extend_schema(request=ReasonInput, responses={204: None})
    def delete(self, request, identifier):
        data = ReasonInput(data=request.data)
        data.is_valid(raise_exception=True)
        delete_staff(request.auth, identifier, data.validated_data["reason"])
        return Response(status=204)


class RoleListView(CookieMutationAPIView):
    permission_classes = [CanManageStaff]

    @extend_schema(responses=RoleOutput(many=True))
    def get(self, request):
        roles = (
            Role.objects.filter(unit=request.auth.staff.unit)
            .prefetch_related("suggested_permissions")
            .order_by("name")
        )
        return Response(RoleOutput(roles, many=True).data)

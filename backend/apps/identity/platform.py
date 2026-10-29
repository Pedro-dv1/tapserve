"""Separate SaaS provisioning surface; no implicit access to tenant operations."""

import time

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from apps.organizations.models import Company, Unit
from common.api import CookieMutationAPIView, page_serializer
from common.network import client_address

from .models import PlatformAuditEvent, PlatformOperator
from .serializers import StrictSerializer
from .services import initialize_roles, rate_limit


class PlatformAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if request.session.get("tapserve_platform") is not True:
            return None
        now = int(time.time())
        issued = request.session.get("platform_issued_at", 0)
        seen = request.session.get("platform_seen_at", 0)
        if (
            type(issued) is not int
            or type(seen) is not int
            or now - issued > 28800
            or now - seen > 900
        ):
            request.session.flush()
            return None
        user = request._request.user
        if not user.is_authenticated or not user.is_active:
            return None
        operator = PlatformOperator.objects.filter(user=user, active=True).first()
        if operator is None:
            request.session.flush()
            return None
        request.session["platform_seen_at"] = now
        return user, operator

    def authenticate_header(self, request):
        return "Session"


class IsPlatformOperator(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, PlatformOperator)


class PlatformView(CookieMutationAPIView):
    authentication_classes = [PlatformAuthentication]
    permission_classes = [IsPlatformOperator]


class PlatformLoginInput(StrictSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class PlatformIdentityOutput(serializers.Serializer):
    username = serializers.CharField()


class PlatformLoginView(PlatformView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=PlatformLoginInput, responses=PlatformIdentityOutput, auth=[])
    def post(self, request):
        if settings.AUTHENTICATION_REQUIRE_HTTPS and not request.is_secure():
            raise PermissionDenied()
        data = PlatformLoginInput(data=request.data)
        data.is_valid(raise_exception=True)
        rate_limit("platform-ip:" + client_address(request), 20)
        rate_limit("platform-user:" + data.validated_data["username"], 5)
        user = authenticate(request=request._request, **data.validated_data)
        operator = PlatformOperator.objects.filter(user=user, active=True).first() if user else None
        if operator is None or user is None:
            raise AuthenticationFailed()
        request.session.flush()
        login(request._request, user)
        request.session.update(
            {
                "tapserve_platform": True,
                "platform_issued_at": int(time.time()),
                "platform_seen_at": int(time.time()),
            }
        )
        request.session.set_expiry(28800)
        PlatformAuditEvent.objects.create(
            operator=operator, action="PLATFORM_LOGIN", resource_id=str(user.pk)
        )
        return Response({"username": user.username})


class PlatformMeView(PlatformView):
    @extend_schema(responses=PlatformIdentityOutput)
    def get(self, request):
        return Response({"username": request.user.username})


class PlatformLogoutView(PlatformView):
    @extend_schema(request=StrictSerializer, responses={204: None})
    def post(self, request):
        data = StrictSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        PlatformAuditEvent.objects.create(
            operator=request.auth, action="PLATFORM_LOGOUT", resource_id=str(request.user.pk)
        )
        logout(request._request)
        return Response(status=204)


class CompanyInput(StrictSerializer):
    name = serializers.CharField(max_length=120)
    slug = serializers.SlugField(max_length=80)


class CompanyOutput(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "slug", "active"]


class UnitInput(CompanyInput):
    company_id = serializers.UUIDField()


class UnitOutput(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["id", "name", "slug", "company_id", "active"]


class PlatformCompanyView(PlatformView):
    @extend_schema(responses=page_serializer(CompanyOutput))
    def get(self, request):
        from rest_framework.pagination import PageNumberPagination

        pager = PageNumberPagination()
        page = pager.paginate_queryset(Company.objects.order_by("name", "id"), request)
        return pager.get_paginated_response(CompanyOutput(page, many=True).data)

    @extend_schema(request=CompanyInput, responses={201: CompanyOutput})
    def post(self, request):
        data = CompanyInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                company = Company.objects.create(**data.validated_data)
                PlatformAuditEvent.objects.create(
                    operator=request.auth, action="COMPANY_CREATED", resource_id=str(company.id)
                )
        except IntegrityError as error:
            raise ValidationError("Código indisponível.") from error
        return Response(CompanyOutput(company).data, status=201)


class PlatformUnitView(PlatformView):
    @extend_schema(responses=page_serializer(UnitOutput))
    def get(self, request):
        from rest_framework.pagination import PageNumberPagination

        pager = PageNumberPagination()
        page = pager.paginate_queryset(Unit.objects.order_by("company_id", "name", "id"), request)
        return pager.get_paginated_response(UnitOutput(page, many=True).data)

    @extend_schema(request=UnitInput, responses={201: UnitOutput})
    def post(self, request):
        data = UnitInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                company = (
                    Company.objects.select_for_update()
                    .filter(id=data.validated_data["company_id"], active=True)
                    .first()
                )
                if company is None:
                    raise ValidationError("Empresa indisponível.")
                unit = Unit.objects.create(
                    company=company,
                    name=data.validated_data["name"],
                    slug=data.validated_data["slug"],
                )
                initialize_roles(unit)
                PlatformAuditEvent.objects.create(
                    operator=request.auth, action="UNIT_CREATED", resource_id=str(unit.id)
                )
        except IntegrityError as error:
            raise ValidationError("Código indisponível.") from error
        return Response(UnitOutput(unit).data, status=201)

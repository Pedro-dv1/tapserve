"""Implemented infrastructure endpoints and consistent safe error envelopes."""

import logging
import secrets
from functools import cache

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("tapserve.api")


@cache
def page_serializer(output):
    class Page(serializers.Serializer):
        count = serializers.IntegerField()
        next = serializers.URLField(allow_null=True)
        previous = serializers.URLField(allow_null=True)
        results = output(many=True)

    Page.__name__ = output.__name__ + "Page"
    return Page


class CookieMutationAPIView(APIView):
    """Enforce CSRF even for anonymous capability and credential endpoints."""

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_authenticate_header(self, request):
        return "Session"


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok", "unavailable"])
    database = serializers.ChoiceField(choices=["ok", "unavailable"])


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: HealthSerializer, 503: HealthSerializer}, auth=[])
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError as error:
            logger.error(
                "database_unavailable",
                extra={
                    "request_id": request.META.get("tapserve.request_id", ""),
                    "error_type": type(error).__name__,
                },
            )
            return Response({"status": "unavailable", "database": "unavailable"}, status=503)
        return Response({"status": "ok", "database": "ok"})


class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=CsrfSerializer, auth=[])
    def get(self, request):
        if "tapserve_browser_nonce" not in request.session:
            request.session["tapserve_browser_nonce"] = secrets.token_urlsafe(32)
        return Response({"csrf_token": get_token(request)})


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "csrf_failed",
                "message": "A validação de segurança falhou. Atualize a página.",
            },
            "request_id": request.META.get("tapserve.request_id", ""),
        },
        status=403,
    )


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request_id = context["request"].META.get("tapserve.request_id", "")
    if response is None:
        logger.error(
            "unexpected_api_error",
            extra={"request_id": request_id, "error_type": type(exc).__name__},
        )
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Não foi possível concluir. Tente novamente.",
                },
                "request_id": request_id,
            },
            status=500,
        )
    codes = {
        400: ("invalid_input", "Confira os dados informados."),
        401: ("unauthenticated", "Acesso expirado. Atualize seu acesso."),
        403: ("forbidden", "Você não tem permissão para esta ação."),
        404: ("not_found", "Não encontrado."),
        405: ("method_not_allowed", "Ação não permitida."),
        409: (
            "conflict",
            "O registro mudou ou o limite foi atingido. Atualize ou solicite ajuda à equipe.",
        ),
        429: ("rate_limited", "Muitas tentativas. Aguarde e tente novamente."),
    }
    code, message = codes.get(
        response.status_code, ("request_failed", "Não foi possível concluir a solicitação.")
    )
    detail: dict[str, object] = {"code": code, "message": message}
    domain_code = exc.get_codes() if hasattr(exc, "get_codes") else None
    if isinstance(domain_code, dict) and len(domain_code) == 1:
        domain_code = next(iter(domain_code.values()))
    if domain_code in ("PRICE_CHANGED", "TAKEAWAY_DISABLED", "TAKEAWAY_NOT_ALLOWED"):
        detail["code"] = domain_code
    if isinstance(exc, ValidationError) and isinstance(exc.detail, dict):
        detail["fields"] = exc.detail
    if response.status_code == 409 and isinstance(getattr(exc, "detail", None), str):
        detail["message"] = str(exc.detail)
    response.data = {"error": detail, "request_id": request_id}
    return response


def not_found(request, exception):
    return JsonResponse(
        {
            "error": {"code": "not_found", "message": "Não encontrado."},
            "request_id": request.META.get("tapserve.request_id", ""),
        },
        status=404,
    )


def server_error(request):
    return JsonResponse(
        {
            "error": {"code": "internal_error", "message": "Não foi possível concluir."},
            "request_id": request.META.get("tapserve.request_id", ""),
        },
        status=500,
    )

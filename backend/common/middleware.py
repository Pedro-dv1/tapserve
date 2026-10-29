"""Request size, correlation and browser policy at the application boundary."""

import logging
import re
import uuid

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger("tapserve.http")


class RequestBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.META["tapserve.request_id"] = uuid.uuid4().hex
        image_upload = (
            bool(
                re.fullmatch(
                    r"/api/v1/admin/products/(?:[0-9a-fA-F-]{36}/(?:image/)?)?", request.path
                )
            )
            and request.content_type == "multipart/form-data"
        )
        body_limit = (
            settings.PRODUCT_IMAGE_MAX_BYTES + 65536
            if request.path == "/api/v1/admin/unit-logo/"
            and request.content_type == "multipart/form-data"
            else settings.PRODUCT_IMAGE_MAX_BYTES + settings.PRODUCT_VIDEO_MAX_BYTES + 65536
            if image_upload
            else 65536
        )
        content_length = request.META.get("CONTENT_LENGTH", "0") or "0"
        if (
            len(content_length) > 10
            or not content_length.isascii()
            or not content_length.isdecimal()
            or int(content_length) > body_limit
        ):
            response = self._error(
                request, 413, "payload_too_large", "O conteúdo enviado excede o limite permitido."
            )
        elif (
            any(
                len(str(value)) > 8192
                for key, value in request.META.items()
                if key.startswith("HTTP_")
            )
            or sum(
                len(key) + len(str(value))
                for key, value in request.META.items()
                if key.startswith("HTTP_")
            )
            > 32768
        ):
            response = self._error(
                request, 431, "headers_too_large", "Cabeçalhos excedem o limite permitido."
            )
        else:
            try:
                if request.path.startswith("/api/") and request.method not in {
                    "GET",
                    "HEAD",
                    "OPTIONS",
                }:
                    if len(request.body) > body_limit:
                        raise RequestDataTooBig
                response = self.get_response(request)
            except RequestDataTooBig:
                response = self._error(
                    request,
                    413,
                    "payload_too_large",
                    "O conteúdo enviado excede o limite permitido.",
                )
        if (
            response.status_code == 404
            and request.path.startswith("/api/")
            and not response.get("Content-Type", "").startswith("application/json")
        ):
            response = self._error(request, 404, "not_found", "Não encontrado.")
        response["X-Request-ID"] = request.META["tapserve.request_id"]
        if not response.has_header("Cache-Control"):
            response["Cache-Control"] = "no-store"
        response["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        logger.info(
            "http_response",
            extra={
                "request_id": request.META["tapserve.request_id"],
                "status": response.status_code,
                "method": request.method,
            },
        )
        return response

    @staticmethod
    def _error(request: HttpRequest, status: int, code: str, message: str) -> JsonResponse:
        return JsonResponse(
            {
                "error": {"code": code, "message": message},
                "request_id": request.META["tapserve.request_id"],
            },
            status=status,
        )

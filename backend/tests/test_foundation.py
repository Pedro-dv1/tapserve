import json
import logging
import os
import secrets
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import DatabaseError, connection
from django.test import Client, override_settings
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.api import CookieMutationAPIView, CsrfView, HealthView
from common.logging import JsonFormatter


class ProbeMutation(CookieMutationAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        return Response({"saved": True})


urlpatterns = [
    path("api/v1/csrf/", CsrfView.as_view()),
    path("api/v1/health/", HealthView.as_view()),
    path("api/v1/test-mutation/", ProbeMutation.as_view()),
]


def production_env() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "TAPSERVE_LOAD_ENV": "0",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DJANGO_ALLOWED_HOSTS": "tapserve.example",
            "CSRF_TRUSTED_ORIGINS": "https://tapserve.example",
            "DJANGO_DEBUG": "False",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_SSL_ROOT_CERT": "/configured/root.crt",
            "TAPSERVE_TOKEN_KEYS": Fernet.generate_key().decode(),
            "PUBLIC_APP_ORIGIN": "https://tapserve.example",
            "TAPSERVE_MEDIA_BUCKET": "configured-private-bucket",
            "TAPSERVE_MEDIA_REGION": "sa-east-1",
        }
    )
    return environment


def import_prod(environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", "import config.settings.prod"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )  # noqa: S603


@pytest.mark.parametrize("secret", [None, "short", "a" * 64])
def test_production_rejects_missing_or_weak_secret(secret):
    environment = production_env()
    if secret is None:
        environment.pop("DJANGO_SECRET_KEY")
    else:
        environment["DJANGO_SECRET_KEY"] = secret
    result = import_prod(environment)
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must" in result.stderr


@pytest.mark.parametrize(
    "key,value",
    [
        ("DJANGO_ALLOWED_HOSTS", "*"),
        ("DJANGO_ALLOWED_HOSTS", "localhost"),
        ("CSRF_TRUSTED_ORIGINS", "http://tapserve.example"),
        ("DJANGO_DEBUG", "True"),
    ],
)
def test_production_rejects_unsafe_config(key, value):
    environment = production_env()
    environment[key] = value
    assert import_prod(environment).returncode != 0


def test_production_import_with_explicit_security_config():
    assert import_prod(production_env()).returncode == 0


@pytest.mark.django_db
def test_health_uses_postgresql_and_sends_browser_headers(client):
    assert connection.vendor == "postgresql"
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response["Cache-Control"] == "no-store"
    assert response["Referrer-Policy"] == "no-referrer"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert len(response["X-Request-ID"]) == 32


@pytest.mark.django_db
def test_health_database_failure_is_not_success(client):
    with patch("common.api.connection.cursor", side_effect=DatabaseError("private detail")):
        response = client.get("/api/v1/health/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert b"private detail" not in response.content


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_csrf_applies_to_anonymous_cookie_mutations():
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post("/api/v1/test-mutation/", {}, content_type="application/json").status_code
        == 403
    )
    response = client.get("/api/v1/csrf/")
    token = response.json()["csrf_token"]
    cookie = response.cookies[settings.CSRF_COOKIE_NAME]
    assert cookie["httponly"] and cookie["samesite"] == "Lax"
    assert response["Cache-Control"] == "no-store"
    assert (
        client.post(
            "/api/v1/test-mutation/", {}, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )
    response = client.post(
        "/api/v1/test-mutation/",
        {},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://evil.example",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert "Access-Control-Allow-Origin" not in response


def test_body_and_header_limits_return_controlled_errors(client):
    response = client.post("/api/v1/health/", data="x" * 65537, content_type="application/json")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert client.get("/api/v1/csrf/", HTTP_ACCEPT="x" * 8193).status_code == 431
    assert (
        client.post(
            "/api/v1/health/", data="{}", content_type="application/json", CONTENT_LENGTH="9" * 5000
        ).status_code
        == 413
    )
    assert (
        client.get(
            "/api/v1/csrf/", **{f"HTTP_X_TEST_{number}": "x" * 2000 for number in range(20)}
        ).status_code
        == 431
    )


def test_unknown_route_and_method_are_safe(client):
    response = client.get("/api/v1/does-not-exist/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    response = client.post("/api/v1/health/", data={}, content_type="application/json")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_log_formatter_omits_exception_and_arbitrary_request_fields():
    record = logging.LogRecord(
        "tapserve",
        logging.ERROR,
        __file__,
        1,
        "database_unavailable",
        (),
        (ValueError, ValueError("sensitive"), None),
    )
    record.request_id = "correlation"
    record.password = "sensitive"
    record.path = "/a/sensitive"
    output = JsonFormatter().format(record)
    assert json.loads(output)["request_id"] == "correlation"
    assert "sensitive" not in output


def test_architecture_traceability_contains_each_section_once():
    import re

    root = Path(__file__).resolve().parents[2]
    matrix = (root / "docs/REQUIREMENTS_TRACEABILITY.md").read_text(encoding="utf-8")
    assert [int(n) for n in re.findall(r"^\| (\d+) \|", matrix, re.MULTILINE)] == list(
        range(1, 135)
    )

"""Shared first-party API settings; production overrides fail closed."""

import os
from ipaddress import ip_network
from pathlib import Path

import environ
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
if (
    os.environ.get("TAPSERVE_LOAD_ENV", "1") == "1"
    and os.environ.get("DJANGO_SETTINGS_MODULE") != "config.settings.prod"
):
    environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 8:
    # No hardcoded or weak fallback credential.
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a random secret of at least 50 characters"
    )

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "apps.organizations",
    "apps.identity",
    "apps.access",
    "apps.catalog",
    "apps.orders",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.RequestBoundaryMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000 -c lock_timeout=5000",
        },
    }
}
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = False
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_FAILURE_VIEW = "common.api.csrf_failure"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
PRODUCT_IMAGE_MAX_BYTES = env.int("PRODUCT_IMAGE_MAX_BYTES", default=2 * 1024 * 1024)
if PRODUCT_IMAGE_MAX_BYTES <= 0:
    raise ImproperlyConfigured("PRODUCT_IMAGE_MAX_BYTES must be positive")
PRODUCT_VIDEO_MAX_BYTES = env.int("PRODUCT_VIDEO_MAX_BYTES", default=25 * 1024 * 1024)
FFPROBE_BINARY = env("FFPROBE_BINARY", default="ffprobe")
if not 0 < PRODUCT_VIDEO_MAX_BYTES <= 100 * 1024 * 1024:
    raise ImproperlyConfigured("PRODUCT_VIDEO_MAX_BYTES must be between 1 and 100 MiB")
DATA_UPLOAD_MAX_MEMORY_SIZE = PRODUCT_IMAGE_MAX_BYTES + PRODUCT_VIDEO_MAX_BYTES + 65536
MEDIA_ROOT = BASE_DIR.parent / ".local" / "media"
STORAGES: dict[str, dict[str, object]] = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
AUTHENTICATION_REQUIRE_HTTPS = True
STAFF_PIN_NETWORKS = env.list("STAFF_PIN_NETWORKS", default=[])
TRUSTED_PROXY_NETWORKS = env.list("TRUSTED_PROXY_NETWORKS", default=[])
for network in [*STAFF_PIN_NETWORKS, *TRUSTED_PROXY_NETWORKS]:
    try:
        if ip_network(network).prefixlen == 0:
            raise ValueError("Unrestricted network")
    except ValueError as error:
        raise ImproperlyConfigured(
            "PIN/proxy networks must be explicit, restricted CIDRs"
        ) from error
DEVICE_COOKIE_NAME = "tapserve-device"
PUBLIC_APP_ORIGIN = env("PUBLIC_APP_ORIGIN", default="http://127.0.0.1:5173").rstrip("/")
TAPSERVE_TOKEN_KEYS = env.list("TAPSERVE_TOKEN_KEYS", default=[])
if len(TAPSERVE_TOKEN_KEYS) > 3:
    raise ImproperlyConfigured("Configure at most three active token encryption keys")
for token_key in TAPSERVE_TOKEN_KEYS:
    try:
        Fernet(token_key)
    except ValueError as error:
        raise ImproperlyConfigured("Token encryption key is invalid") from error

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.identity.authentication.StaffSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.api.exception_handler",
}
SPECTACULAR_SETTINGS = {
    "COMPONENT_SPLIT_REQUEST": True,
    "TITLE": "TapServe API",
    "DESCRIPTION": "First-party operational API. Only implemented endpoints are included.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "HealthStateEnum": ["ok", "unavailable"],
        "OrderItemStateEnum": "apps.orders.models.OrderItem.State",
        "FulfillmentModeEnum": "apps.orders.models.OrderItem.Fulfillment",
        "MenuLayoutEnum": ["EDITORIAL", "COMPACT"],
        "ItemTransitionTargetEnum": [
            "ACCEPTED",
            "REJECTED",
            "PREPARING",
            "READY",
            "DELIVERING",
            "DELIVERED",
        ],
        "ServiceRequestStateEnum": "apps.orders.models.ServiceRequest.State",
        "ServiceRequestTargetEnum": ["ASSIGNED", "RESOLVED", "CANCELLED"],
    },
}
# Native PG notifications and durable event rows power realtime; no channel-layer substitute.
CHANNEL_LAYERS: dict[str, object] = {}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "common.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    # Django's request logger includes full paths; capability URLs must never enter it.
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "filters": ["safe_request"],
            "propagate": False,
        },
        "django.server": {"handlers": ["console"], "filters": ["safe_request"], "propagate": False},
    },
    "filters": {"safe_request": {"()": "common.logging.SuppressRequestDetails"}},
}

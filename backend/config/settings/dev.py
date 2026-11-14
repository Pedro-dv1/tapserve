from .base import *  # noqa: F403
from .base import (
    BASE_DIR,
    DATABASES,
    LOCAL_ENVIRONMENT,
    PUBLIC_APP_ORIGIN,
    TAPSERVE_TOKEN_KEYS,
    env,
)

DEBUG = True

ALLOWED_HOSTS = env.list(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"]
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CSRF_TRUSTED_ORIGINS = env.list(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)

SECURE_SSL_REDIRECT = False
AUTHENTICATION_REQUIRE_HTTPS = False

STAFF_PIN_NETWORKS = env.list(  # noqa: F405
    "STAFF_PIN_NETWORKS", default=["127.0.0.1/32", "::1/128"]
)

if LOCAL_ENVIRONMENT:
    from django.core.exceptions import ImproperlyConfigured

    expected_module = f"config.settings.{LOCAL_ENVIRONMENT}"
    if (
        env("DJANGO_SETTINGS_MODULE", default=expected_module) != expected_module
        or DATABASES["default"]["NAME"] != f"tapserve_{LOCAL_ENVIRONMENT}"
        or DATABASES["default"]["USER"] != f"tapserve_{LOCAL_ENVIRONMENT}_user"
        or DATABASES["default"]["HOST"] not in {"127.0.0.1", "localhost", "::1"}
        or not DATABASES["default"]["PASSWORD"]
        or not TAPSERVE_TOKEN_KEYS
    ):
        raise ImproperlyConfigured("Local profile/database/role/credentials mismatch")
    frontend_port = env.int("FRONTEND_PORT")
    backend_port = env.int("BACKEND_PORT")
    if (
        not all(1024 <= port <= 65535 for port in (frontend_port, backend_port))
        or frontend_port == backend_port
        or PUBLIC_APP_ORIGIN != f"http://127.0.0.1:{frontend_port}"
        or set(ALLOWED_HOSTS) != {"localhost", "127.0.0.1", "[::1]"}
        or set(CSRF_TRUSTED_ORIGINS)
        != {f"http://127.0.0.1:{frontend_port}", f"http://localhost:{frontend_port}"}
        or env.list("CORS_ALLOWED_ORIGINS", default=[])
    ):
        raise ImproperlyConfigured("Local profiles require exact loopback hosts and same-origin proxy")
    DEBUG = env.bool("DJANGO_DEBUG", default=LOCAL_ENVIRONMENT == "dev")
    SESSION_COOKIE_NAME = f"tapserve-{LOCAL_ENVIRONMENT}-session"
    CSRF_COOKIE_NAME = f"tapserve-{LOCAL_ENVIRONMENT}-csrf"
    DEVICE_COOKIE_NAME = f"tapserve-{LOCAL_ENVIRONMENT}-device"
    BROWSER_COOKIE_NAME = f"tapserve-{LOCAL_ENVIRONMENT}-browser"
    SESSION_COOKIE_DOMAIN = None
    CSRF_COOKIE_DOMAIN = None
    SESSION_COOKIE_PATH = "/"
    CSRF_COOKIE_PATH = "/"
    MEDIA_ROOT = BASE_DIR.parent / ".local" / "environments" / LOCAL_ENVIRONMENT / "media"
    FILE_UPLOAD_TEMP_DIR = str(MEDIA_ROOT.parent / "tmp")

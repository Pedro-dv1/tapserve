from .base import *  # noqa: F403

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

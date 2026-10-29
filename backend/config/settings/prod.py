from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import (
    ALLOWED_HOSTS,
    CSRF_TRUSTED_ORIGINS,
    DATABASES,
    PUBLIC_APP_ORIGIN,
    TAPSERVE_TOKEN_KEYS,
    env,
)

if not ALLOWED_HOSTS or any(
    host in {"*", "localhost", "127.0.0.1"} or host.startswith(".") for host in ALLOWED_HOSTS
):
    raise ImproperlyConfigured("Production requires explicit non-wildcard public hosts")
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") or "*" in origin for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("Production requires explicit HTTPS CSRF origins")
if env.bool("DJANGO_DEBUG", default=False):
    raise ImproperlyConfigured("Production cannot enable DJANGO_DEBUG")
origin = urlsplit(PUBLIC_APP_ORIGIN)
if (
    not TAPSERVE_TOKEN_KEYS
    or origin.scheme != "https"
    or not origin.netloc
    or origin.hostname in {"localhost", "127.0.0.1", "::1"}
    or origin.path
    or origin.query
    or origin.fragment
    or origin.username
    or origin.password
):
    raise ImproperlyConfigured(
        "Production requires independent token keys and an explicit public HTTPS app origin"
    )
DATABASES["default"]["OPTIONS"]["sslmode"] = "verify-full"
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("TAPSERVE_MEDIA_BUCKET"),
            "region_name": env("TAPSERVE_MEDIA_REGION"),
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
            "object_parameters": {
                "CacheControl": "private, no-store",
                "ServerSideEncryption": "AES256",
            },
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
DATABASES["default"]["OPTIONS"]["sslrootcert"] = env("POSTGRES_SSL_ROOT_CERT")
SESSION_COOKIE_NAME = "__Host-tapserve-session"
CSRF_COOKIE_NAME = "__Host-tapserve-csrf"
DEVICE_COOKIE_NAME = "__Host-tapserve-device"
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
# Trust SECURE_PROXY_SSL_HEADER only after a deployment verifies overwritten headers.

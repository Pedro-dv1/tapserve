import os
import re
from pathlib import Path

import environ

# An isolated test cluster is optional elsewhere; OS configuration still takes precedence.
environ.Env.read_env(Path(__file__).resolve().parents[3] / ".local" / "test.env", overwrite=False)

from .base import *  # noqa: E402,F403

# Native transport tests start Daphne separately; its runserver app selects Twisted globally.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "daphne"]  # noqa: F405

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ["http://testserver"]
SECURE_SSL_REDIRECT = False
AUTHENTICATION_REQUIRE_HTTPS = False
STAFF_PIN_NETWORKS = ["127.0.0.1/32", "::1/128"]
schema = os.environ.get("TAPSERVE_TEST_SCHEMA")
if schema:
    if not re.fullmatch(r"tapserve_test_[0-9a-f]{32}", schema):
        raise ValueError("Only an exclusively created test schema may be selected")
    DATABASES["default"]["OPTIONS"]["options"] += f" -c search_path={schema}"  # noqa: F405

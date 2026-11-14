"""Persistent local QA: the same authentication and authorization as DEV, without debug."""

from django.core.exceptions import ImproperlyConfigured

from .dev import *  # noqa: F403
from .dev import LOCAL_ENVIRONMENT

if LOCAL_ENVIRONMENT != "qa":
    raise ImproperlyConfigured("QA requires TAPSERVE_ENV=qa and its dedicated env file")

DEBUG = False

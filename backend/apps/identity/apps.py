from django.apps import AppConfig


class IdentityConfig(AppConfig):
    name = "apps.identity"

    def ready(self):
        from . import schema  # noqa: F401

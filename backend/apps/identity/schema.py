from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class StaffCookieScheme(OpenApiAuthenticationExtension):
    target_class = "apps.identity.authentication.StaffSessionAuthentication"
    name = "staffSession"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.SESSION_COOKIE_NAME,
            "description": "Revocable staff session; unsafe methods additionally require X-CSRFToken.",
        }


class PlatformCookieScheme(StaffCookieScheme):
    target_class = "apps.identity.platform.PlatformAuthentication"
    name = "platformSession"


class DeviceCookieScheme(StaffCookieScheme):
    target_class = "apps.access.views.DeviceAuthentication"
    name = "deviceAccess"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.DEVICE_COOKIE_NAME,
            "description": "Point-scoped capability, expires after twelve hours and can be revoked. Mutations require X-CSRFToken.",
        }

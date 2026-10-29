import asyncio
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
django_application = get_asgi_application()

# Models must be imported after Django populates the application registry.
from apps.orders.realtime import DomainConsumer  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_application,
        "websocket": OriginValidator(
            URLRouter(
                [
                    path("ws/v1/public/", DomainConsumer.as_asgi()),
                    path("ws/v1/staff/", DomainConsumer.as_asgi()),
                ]
            ),
            settings.CSRF_TRUSTED_ORIGINS,
        ),
    }
)

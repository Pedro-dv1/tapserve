"""Unit branding reuses the catalog's bounded raster validation and private storage."""

import hashlib
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse
from rest_framework.exceptions import NotFound

from apps.catalog.services import delete_image, normalize_image
from apps.identity.models import AuditEvent
from apps.identity.permissions import require_permission

from .models import Unit


def logo_url(unit, realm="public"):
    if not unit.logo_key:
        return None
    version = hashlib.sha256(unit.logo_key.encode()).hexdigest()[:16]
    return f"/api/v1/{realm}/unit-logo/image/?v={version}"


def logo_response(unit):
    if not unit.logo_key:
        raise NotFound()
    try:
        file = default_storage.open(unit.logo_key, "rb")
    except FileNotFoundError as error:
        raise NotFound() from error
    return FileResponse(file, content_type="image/webp", filename="logo.webp")


def set_logo(identity, upload=None):
    # ASVS V8.2/V8.3: scope comes from the authenticated unit, never the request.
    require_permission(identity, "MANAGE_SETTINGS")
    key = ""
    if upload is not None:
        # ASVS V5.2/V5.3: decode bounded raster content and use a generated storage key.
        normalized = normalize_image(upload, preserve_alpha=True)
        key = default_storage.save(
            f"logos/{identity.staff.unit_id}/{uuid.uuid4()}.webp", ContentFile(normalized)
        )
    try:
        with transaction.atomic():
            unit = Unit.objects.select_for_update().get(id=identity.staff.unit_id)
            require_permission(identity, "MANAGE_SETTINGS")
            old = unit.logo_key
            unit.logo_key = key
            unit.save(update_fields=["logo_key"])
            AuditEvent.objects.create(
                unit=unit,
                staff=identity.staff,
                action="UNIT_LOGO_UPDATED" if key else "UNIT_LOGO_REMOVED",
                resource_id=str(unit.id),
            )
            if old:
                transaction.on_commit(lambda: delete_image(old), robust=True)
    except Exception:
        if key:
            delete_image(key)
        raise
    return unit

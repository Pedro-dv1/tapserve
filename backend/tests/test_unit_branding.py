import secrets
import shutil
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.access.models import ServicePoint
from apps.access.services import cipher, digest
from apps.identity.models import AuditEvent
from apps.organizations.models import Unit
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client

BASE = "/api/v1/admin/unit-logo/"
PUBLIC = "/api/v1/public/unit-logo/image/"


@pytest.fixture
def logo_media(settings):
    root = Path(__file__).resolve().parents[2] / ".local"
    directory = root / ("logo-test-" + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    settings.MEDIA_ROOT = directory
    try:
        yield directory
    finally:
        assert directory.resolve().parent == root.resolve()
        shutil.rmtree(directory)


def image_file(size=(240, 60), color=(20, 30, 40, 0)):
    data = BytesIO()
    Image.new("RGBA", size, color).save(data, "PNG")
    return SimpleUploadedFile("untrusted.png", data.getvalue(), content_type="image/png")


def upload(client, data):
    from django.test.client import MULTIPART_CONTENT, encode_multipart

    token = client.get("/api/v1/csrf/").json()["csrf_token"]
    return client.put(
        BASE,
        encode_multipart("BoUnDaRyStRiNg", data),
        content_type=MULTIPART_CONTENT,
        HTTP_X_CSRFTOKEN=token,
    )


@pytest.mark.parametrize("size", [(240, 60), (60, 240), (120, 120)])
@pytest.mark.django_db(transaction=True)
def test_logo_upload_replace_remove_preserve_ratio_alpha_and_context(
    identity_data, point_data, logo_media, size
):
    admin, public = owner_client(identity_data), customer(point_data[1])
    assert admin.get(BASE).json()["logo_url"] is None
    assert public.get("/api/v1/public/context/").json()["unit_logo_url"] is None
    assert public.get(PUBLIC).status_code == 404
    response = upload(admin, {"image": image_file(size)})
    assert response.status_code == 200, response.content
    unit = identity_data[0]
    unit.refresh_from_db()
    old = unit.logo_key
    assert old.startswith(f"logos/{unit.id}/") and default_storage.exists(old)
    assert old not in str(response.json())
    with default_storage.open(old, "rb") as stream, Image.open(stream) as image:
        assert image.size == size and image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0
    url = public.get("/api/v1/public/context/").json()["unit_logo_url"]
    rendered = public.get(url)
    assert rendered.status_code == 200 and rendered["Content-Type"] == "image/webp"
    rendered.close()
    assert upload(admin, {"image": image_file((80, 80))}).status_code == 200
    assert not default_storage.exists(old)
    assert public.get("/api/v1/public/context/").json()["unit_logo_url"] != url
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    assert admin.delete(BASE, HTTP_X_CSRFTOKEN=token).json()["logo_url"] is None
    assert public.get(PUBLIC).status_code == 404
    assert AuditEvent.objects.filter(action="UNIT_LOGO_UPDATED", unit=unit).count() == 2
    assert AuditEvent.objects.filter(action="UNIT_LOGO_REMOVED", unit=unit).count() == 1


def test_logo_permissions_csrf_and_unit_isolation(identity_data, point_data, logo_media):
    admin, waiter, public = owner_client(identity_data), pin_client(), customer(point_data[1])
    assert Client().get(BASE).status_code == 401
    assert Client().get(PUBLIC).status_code == 401
    assert waiter.get(BASE).status_code == 403
    assert upload(waiter, {"image": image_file()}).status_code == 403
    assert admin.put(BASE).status_code == 403
    assert admin.delete(BASE).status_code == 403
    assert (
        upload(
            admin, {"image": image_file(), "unit_id": str(identity_data[3][1].unit_id)}
        ).status_code
        == 400
    )
    assert upload(admin, {"image": image_file()}).status_code == 200
    token = secrets.token_urlsafe(32)
    foreign = ServicePoint.objects.create(
        unit=identity_data[3][1].unit,
        name="Foreign",
        type="TABLE",
        number=1,
        token_digest=digest(token),
        token_ciphertext=cipher().encrypt(token.encode()),
    )
    other = customer(token)
    assert other.get(PUBLIC).status_code == 404
    assert other.get(BASE).status_code == 401
    foreign.unit.refresh_from_db()
    assert not foreign.unit.logo_key
    identity_data[1].permissions.clear()
    assert admin.get(BASE).status_code == 403
    assert upload(admin, {"image": image_file()}).status_code == 403
    response = public.get(PUBLIC + f"?unit_id={foreign.unit_id}")
    assert response.status_code == 200
    response.close()


def test_invalid_logo_keeps_existing_file_and_large_upload_has_bounded_request(
    identity_data, logo_media, settings
):
    admin = owner_client(identity_data)
    assert upload(admin, {"image": image_file()}).status_code == 200
    unit = identity_data[0]
    unit.refresh_from_db()
    old = unit.logo_key
    invalid = [
        SimpleUploadedFile("fake.png", b"<svg><script>alert(1)</script></svg>", "image/png"),
        image_file((2001, 2000)),
        SimpleUploadedFile("large.png", b"x" * (settings.PRODUCT_IMAGE_MAX_BYTES + 1), "image/png"),
    ]
    for file in invalid:
        assert upload(admin, {"image": file}).status_code == 400
    assert upload(admin, {"image": [image_file(), image_file()]}).status_code == 400
    unit.refresh_from_db()
    assert unit.logo_key == old and default_storage.exists(old)
    assert AuditEvent.objects.filter(action="UNIT_LOGO_UPDATED").count() == 1
    # The logo route allows image uploads but never inherits the product video allowance.
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    assert (
        admin.put(
            BASE,
            b"",
            content_type="multipart/form-data; boundary=test",
            CONTENT_LENGTH=str(settings.PRODUCT_IMAGE_MAX_BYTES + 65537),
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 413
    )


def test_logo_database_failure_cleans_new_file_and_preserves_previous(
    identity_data, logo_media, monkeypatch
):
    admin = owner_client(identity_data)
    assert upload(admin, {"image": image_file()}).status_code == 200
    unit = identity_data[0]
    unit.refresh_from_db()
    old = unit.logo_key
    files = set(logo_media.rglob("*.webp"))
    save = Unit.save

    def fail(self, *args, **kwargs):
        if kwargs.get("update_fields") == ["logo_key"]:
            raise RuntimeError("injected persistence failure")
        return save(self, *args, **kwargs)

    monkeypatch.setattr(Unit, "save", fail)
    assert upload(admin, {"image": image_file()}).status_code == 500
    unit.refresh_from_db()
    assert unit.logo_key == old and set(logo_media.rglob("*.webp")) == files
    assert AuditEvent.objects.filter(action="UNIT_LOGO_UPDATED").count() == 1

import uuid
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.test.utils import CaptureQueriesContext
from PIL import Image

from apps.catalog.models import Category, Menu, Product, ProductionSector, ProductPhoto
from apps.orders.models import DomainEvent
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client


@pytest.fixture
def media_root():
    # Windows sandbox rejects pytest's owner-only temp directory ACL; keep synthetic media locally.
    root = Path(__file__).resolve().parents[2] / ".local" / ("v2-media-" + uuid.uuid4().hex)
    root.mkdir()
    return root


def image_file():
    output = BytesIO()
    Image.new("RGB", (120, 90), color="orange").save(output, "PNG")
    return SimpleUploadedFile("photo.png", output.getvalue(), content_type="image/png")


def upload(client, url, *, key=None, position=0, image=None):
    token = client.get("/api/v1/csrf/").json()["csrf_token"]
    return client.post(
        url,
        {
            "idempotency_key": key or str(uuid.uuid4()),
            "image": image if image is not None else image_file(),
            "position": position,
            "alt_text": "Prato servido",
        },
        HTTP_X_CSRFTOKEN=token,
    )


def test_gallery_real_upload_order_retry_removal_quota_and_scope(
    identity_data, point_data, catalog_data, media_root
):
    admin = owner_client(identity_data)
    public = customer(point_data[1])
    product = catalog_data[3]
    base = f"/api/v1/admin/products/{product.id}/photos/"
    with override_settings(MEDIA_ROOT=media_root):
        key = str(uuid.uuid4())
        created = upload(admin, base, key=key, position=5)
        assert created.status_code == 201, created.content
        assert upload(admin, base, key=key, position=5).json() == created.json()
        assert ProductPhoto.objects.count() == 1
        photo = ProductPhoto.objects.get()
        assert photo.image_key.startswith(f"products/{product.unit_id}/")
        assert photo.image_key.endswith(".webp")
        public_url = f"/api/v1/public/products/{product.id}/photos/{photo.id}/"
        response = public.get(public_url)
        assert response.status_code == 200 and response["Content-Type"] == "image/webp"
        assert response["Cache-Control"] == "private, no-cache"
        assert b"".join(response.streaming_content).startswith(b"RIFF")
        token = admin.get("/api/v1/csrf/").json()["csrf_token"]
        assert (
            admin.patch(
                f"{base}{photo.id}/",
                {"position": 1, "alt_text": "Vista lateral"},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 200
        )
        for position in range(2, 7):
            assert upload(admin, base, position=position).status_code == 201
        assert upload(admin, base).status_code == 400
        detail = public.get(f"/api/v1/public/products/{product.id}/").json()
        assert [row["position"] for row in detail["photos"]] == [1, 2, 3, 4, 5, 6]
        assert detail["photos"][0]["alt_text"] == "Vista lateral"
        assert pin_client().get(base).status_code == 403
        assert public.get(base).status_code == 401
        foreign_unit = identity_data[3][0].unit
        menu = Menu.objects.create(unit=foreign_unit, name="Outro")
        category = Category.objects.create(menu=menu, name="Outra")
        sector = ProductionSector.objects.create(unit=foreign_unit, name="Outro")
        foreign = Product.objects.create(
            unit=foreign_unit,
            category=category,
            production_sector=sector,
            base_price="10.00",
            name="Outro",
        )
        assert admin.get(f"/api/v1/admin/products/{foreign.id}/photos/").status_code == 404
        assert (
            public.get(f"/api/v1/public/products/{foreign.id}/photos/{photo.id}/").status_code
            == 404
        )
        assert admin.delete(f"{base}{photo.id}/", HTTP_X_CSRFTOKEN=token).status_code == 204
        assert public.get(public_url).status_code == 404
        assert ProductPhoto.objects.get(id=photo.id).active is False
        assert ProductPhoto.objects.count() == 6
        assert DomainEvent.objects.filter(kind="CATALOG_CHANGED").exists()


def test_gallery_rejects_false_mime_oversize_remote_urls_and_mass_assignment(
    identity_data, catalog_data, media_root
):
    admin = owner_client(identity_data)
    base = f"/api/v1/admin/products/{catalog_data[3].id}/photos/"
    with override_settings(MEDIA_ROOT=media_root):
        disguised = SimpleUploadedFile(
            "photo.png", b"<script>bad</script>", content_type="image/png"
        )
        assert upload(admin, base, image=disguised).status_code == 400
        with override_settings(PRODUCT_IMAGE_MAX_BYTES=8):
            assert upload(admin, base).status_code == 400
        token = admin.get("/api/v1/csrf/").json()["csrf_token"]
        for fields in [
            {"url": "http://127.0.0.1/private"},
            {"product": str(catalog_data[3].id)},
            {"unit_id": str(identity_data[0].id)},
        ]:
            assert (
                admin.post(
                    base,
                    {"idempotency_key": str(uuid.uuid4()), "image": image_file(), **fields},
                    HTTP_X_CSRFTOKEN=token,
                ).status_code
                == 400
            )
        assert ProductPhoto.objects.count() == 0
        assert list(media_root.rglob("*.webp")) == []


def test_editorial_hero_metadata_and_list_remain_scoped_and_light(
    identity_data, point_data, catalog_data, media_root
):
    public = customer(point_data[1])
    admin = owner_client(identity_data)
    product = catalog_data[3]
    assert public.get("/api/v1/public/menu/").json()["presentation"] == {
        "layout": "EDITORIAL",
        "hero": None,
        "popular": [],
    }
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    with override_settings(MEDIA_ROOT=media_root):
        assert (
            admin.patch(
                f"/api/v1/admin/products/{product.id}/",
                encode_multipart(
                    BOUNDARY,
                    {
                        "image": image_file(),
                        "featured": "true",
                        "long_description": "Feito na hora",
                        "ingredients": "Pão e queijo",
                        "serving_info": "Serve 1 pessoa",
                        "allergen_info": "Contém leite e trigo",
                    },
                ),
                content_type=MULTIPART_CONTENT,
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 200
        )
        detail = public.get(f"/api/v1/public/products/{product.id}/").json()
        assert (
            detail["ingredients"] == "Pão e queijo"
            and detail["allergen_info"] == "Contém leite e trigo"
        )
        assert detail["photos"] == []
        assert len(detail["image_version"]) == 16
        with CaptureQueriesContext(connection) as first:
            menu = public.get("/api/v1/public/menu/").json()
        assert menu["presentation"]["hero"]["id"] == str(product.id)
        assert "photos" not in menu["results"][0] and "long_description" not in menu["results"][0]
        assert upload(admin, f"/api/v1/admin/products/{product.id}/photos/").status_code == 201
        with CaptureQueriesContext(connection) as second:
            public.get("/api/v1/public/menu/")
        assert len(second) == len(first)
        old_version = detail["image_version"]
        assert (
            admin.patch(
                f"/api/v1/admin/products/{product.id}/",
                encode_multipart(BOUNDARY, {"image": image_file()}),
                content_type=MULTIPART_CONTENT,
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 200
        )
        assert (
            public.get(f"/api/v1/public/products/{product.id}/").json()["image_version"]
            != old_version
        )
        Product.objects.filter(id=product.id).update(available=False)
        assert public.get("/api/v1/public/menu/").json()["presentation"]["hero"] is None


def test_settings_are_optimistic_audited_and_cannot_enable_public_pickup(identity_data):
    admin = owner_client(identity_data)
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "expected_window_minutes": 3,
        "customer_edit_window_minutes": 3,
        "expected_settings": {"table_takeaway_enabled": False, "menu_layout": "EDITORIAL"},
        "table_takeaway_enabled": True,
        "leftover_packaging_enabled": True,
        "menu_layout": "COMPACT",
    }
    url = "/api/v1/admin/order-policy/"
    changed = admin.put(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert changed.status_code == 200 and changed.json()["public_pickup_enabled"] is False
    assert (
        admin.put(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token).json()
        == changed.json()
    )
    assert (
        admin.put(
            url,
            {**body, "idempotency_key": str(uuid.uuid4())},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 409
    )
    assert (
        admin.put(
            url,
            {**body, "public_pickup_enabled": True},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 400
    )

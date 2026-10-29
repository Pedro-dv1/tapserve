from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Category, Menu, Option, OptionGroup, Product
from apps.catalog.services import normalize_image, quote
from tests.test_access import customer
from tests.test_identity import owner_client, post_with_csrf


def test_public_menu_and_quote_enforce_scope_choices_and_stale_availability(
    catalog_data, point_data
):
    client = customer(point_data[1])
    product, group, option = catalog_data[3:]
    menu = client.get("/api/v1/public/menu/")
    assert menu.status_code == 200 and menu.json()["count"] == 1
    detail = client.get(f"/api/v1/public/products/{product.id}/")
    assert detail.status_code == 200 and detail.json()["groups"][0]["options"][0]["id"] == str(
        option.id
    )
    body = {"product_id": str(product.id), "quantity": 3, "option_ids": [str(option.id)]}
    result = post_with_csrf(client, "/api/v1/public/quote/", body)
    assert result.status_code == 200
    assert result.json()["unit_price"] == "12.35" and result.json()["line_total"] == "37.05"
    for invalid in (
        {**body, "quantity": 0},
        {**body, "option_ids": []},
        {**body, "option_ids": [str(option.id)] * 2},
        {**body, "price": "0.01"},
        {**body, "unit_id": str(point_data[0].unit_id)},
    ):
        assert post_with_csrf(client, "/api/v1/public/quote/", invalid).status_code == 400
    product.available = False
    product.save()
    assert client.get("/api/v1/public/menu/").json()["count"] == 0
    assert client.get(f"/api/v1/public/products/{product.id}/").status_code == 404
    assert post_with_csrf(client, "/api/v1/public/quote/", body).status_code == 400


def test_multiple_group_bounds_and_unknown_options_are_rejected(catalog_data):
    _, _, _, product, group, option = catalog_data
    group.selection_type = "MULTIPLE"
    group.min_choices = 1
    group.max_choices = 2
    group.save()
    second = Option.objects.create(group=group, name="Extra", additional_price=Decimal("0.35"))
    third = Option.objects.create(group=group, name="Third")
    assert (
        quote(
            product.unit,
            {"product_id": product.id, "quantity": 1, "option_ids": [option.id, second.id]},
        )["line_total"]
        == "12.70"
    )
    with pytest.raises(ValidationError):
        quote(
            product.unit,
            {
                "product_id": product.id,
                "quantity": 1,
                "option_ids": [option.id, second.id, third.id],
            },
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        OptionGroup.objects.filter(id=group.id).update(min_choices=3, max_choices=2)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(id=product.id).update(base_price=Decimal("-0.01"))


def test_catalog_foreign_keys_and_methods_cannot_cross_units(catalog_data, identity_data):
    admin = owner_client(identity_data)
    foreign_unit = identity_data[3][0].unit
    foreign_menu = Menu.objects.create(unit=foreign_unit, name="Foreign")
    foreign_category = Category.objects.create(menu=foreign_menu, name="Foreign")
    product = catalog_data[3]
    csrf = admin.get("/api/v1/csrf/").json()["csrf_token"]
    assert (
        admin.patch(
            f"/api/v1/admin/products/{product.id}/",
            {"category": str(foreign_category.id)},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 400
    )
    assert admin.get(f"/api/v1/admin/categories/{foreign_category.id}/").status_code == 404
    assert (
        admin.patch(
            f"/api/v1/admin/categories/{foreign_category.id}/",
            {"name": "Changed"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 404
    )
    assert (
        admin.delete(
            f"/api/v1/admin/categories/{foreign_category.id}/",
            {"reason": "Test"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 404
    )
    assert post_with_csrf(admin, f"/api/v1/admin/products/{product.id}/", {}).status_code == 405
    assert (
        admin.patch(
            "/api/v1/admin/products/", {}, content_type="application/json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 405
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(id=product.id).update(category=foreign_category)
    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.filter(id=catalog_data[1].id).update(menu=foreign_menu)


def test_images_are_reencoded_and_invalid_content_is_rejected(
    catalog_data, point_data, identity_data, settings
):
    output = BytesIO()
    Image.new("RGB", (16, 16), "red").save(output, format="PNG")
    image = SimpleUploadedFile("../../fake.svg", output.getvalue(), content_type="image/svg+xml")
    normalized = normalize_image(image)
    with Image.open(BytesIO(normalized)) as opened:
        assert opened.format == "WEBP" and opened.size == (16, 16)
        assert not opened.getexif()
    for raw in (b'<svg onload="alert(1)"/>', b"not-an-image", output.getvalue()[:20]):
        with pytest.raises(ValidationError):
            normalize_image(SimpleUploadedFile("fake.png", raw, content_type="image/png"))
    admin = owner_client(identity_data)
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    product = catalog_data[3]
    response = admin.post(
        f"/api/v1/admin/products/{product.id}/image/",
        {"image": SimpleUploadedFile("photo.png", output.getvalue(), content_type="image/png")},
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200 and response.json()["has_image"]
    product.refresh_from_db()
    assert ".." not in product.image_key and product.image_key.endswith(".webp")
    from django.core.files.storage import default_storage

    try:
        public = customer(point_data[1]).get(f"/api/v1/public/products/{product.id}/image/")
        assert public.status_code == 200 and public["Content-Type"] == "image/webp"
        public.close()
    finally:
        default_storage.delete(product.image_key)

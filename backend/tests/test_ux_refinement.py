"""Regression coverage with real authorization, persistence and PostgreSQL pagination."""

from decimal import Decimal

import pytest
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from apps.catalog.models import Category, Menu, Product, ProductionSector
from apps.orders.models import OrderItem
from tests import test_v2_menu
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_operational_redesign import session_item
from tests.test_orders import payload
from tests.test_production import mutate
from tests.test_v2_menu import image_file

media_root = test_v2_menu.media_root


def test_search_is_accent_insensitive_ranked_paginated_and_scoped(
    identity_data, point_data, catalog_data
):
    menu, category, sector, product = catalog_data[:4]
    Product.objects.filter(pk=product.pk).update(name="Hambúrguer")
    Product.objects.bulk_create(
        [
            Product(
                unit=product.unit,
                category=category,
                production_sector=sector,
                name=f"Hambúrguer {index:03}",
                base_price=Decimal("12.00"),
            )
            for index in range(55)
        ]
    )
    inactive = Product.objects.create(
        unit=product.unit,
        category=category,
        production_sector=sector,
        name="Hambúrguer desativado",
        active=False,
        base_price=Decimal("12.00"),
    )
    foreign_menu = Menu.objects.create(unit=identity_data[3][0].unit, name="Outro")
    foreign_category = Category.objects.create(menu=foreign_menu, name="Outra")
    foreign_sector = ProductionSector.objects.create(unit=foreign_menu.unit, name="Outra")
    Product.objects.create(
        unit=foreign_menu.unit,
        category=foreign_category,
        production_sector=foreign_sector,
        name="Hambúrguer de outra unidade",
        base_price=Decimal("1.00"),
    )
    admin = owner_client(identity_data)
    query = {"search": "  HAMBURGUER  ", "menu": str(menu.id), "active": "true"}
    first = admin.get("/api/v1/admin/products/", query)
    assert first.status_code == 200
    assert first.json()["count"] == 56
    assert first.json()["results"][0]["id"] == str(product.id)
    second = admin.get("/api/v1/admin/products/", {**query, "page": 2}).json()
    assert len(second["results"]) == 6
    assert not {row["id"] for row in first.json()["results"]} & {
        row["id"] for row in second["results"]
    }
    assert all(row["id"] != str(inactive.id) for row in second["results"])
    waiter = pin_client()
    path = f"/api/v1/staff/tables/{point_data[0].id}/menu/"
    assert waiter.get(path, {"search": "hamburguer"}).json()["count"] == 56
    assert waiter.get(path, {"search": "hamburguer", "page": 2}).json()["count"] == 56
    assert waiter.get("/api/v1/admin/products/").status_code == 403
    assert admin.get("/api/v1/admin/products/?search=inexistente").json()["count"] == 0
    assert admin.get("/api/v1/admin/products/?search=%25%27").status_code == 200
    assert admin.get("/api/v1/admin/products/?unit_id=other").status_code == 400


@pytest.mark.parametrize("terminal_status", ["CANCELLED", "REJECTED"])
def test_popular_highlight_uses_sales_images_and_availability(
    identity_data, point_data, catalog_data, settings, media_root, terminal_status
):
    settings.MEDIA_ROOT = media_root
    admin = owner_client(identity_data)
    public = customer(point_data[1])
    product = catalog_data[3]
    assert public.get("/api/v1/public/menu/").json()["presentation"]["popular"] == []
    csrf = admin.get("/api/v1/csrf/").json()["csrf_token"]
    uploaded = admin.patch(
        f"/api/v1/admin/products/{product.id}/",
        encode_multipart(BOUNDARY, {"image": image_file()}),
        content_type=MULTIPART_CONTENT,
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert uploaded.status_code == 200
    assert (
        post_with_csrf(public, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    highlights = public.get("/api/v1/public/menu/").json()["presentation"]["popular"]
    assert [row["id"] for row in highlights] == [str(product.id)]
    assert highlights[0]["ordered_quantity"] == 2 and highlights[0]["has_image"]
    assert public.get("/api/v1/public/menu/?search=Lanche").json()["presentation"]["popular"] == []
    Product.objects.filter(pk=product.pk).update(available=False)
    assert public.get("/api/v1/public/menu/").json()["presentation"]["popular"] == []
    Product.objects.filter(pk=product.pk).update(available=True)
    OrderItem.objects.update(status=terminal_status)
    assert public.get("/api/v1/public/menu/").json()["presentation"]["popular"] == []


def test_delivery_attention_survives_opening_orders_and_claim_until_actual_delivery(
    identity_data, point_data, catalog_data
):
    public = customer(point_data[1])
    admin = owner_client(identity_data)
    assert (
        post_with_csrf(public, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    item = OrderItem.objects.get()
    attention = "/api/v1/staff/deliveries/?attention=true"
    assert admin.get(attention).json()["count"] == 0
    for previous, target in [
        ("NEW", "ACCEPTED"),
        ("ACCEPTED", "PREPARING"),
        ("PREPARING", "READY"),
    ]:
        assert mutate(admin, item, previous, target).status_code == 200
    assert admin.get(attention).json()["count"] == 1
    assert admin.get("/api/v1/staff/orders/").status_code == 200
    assert admin.get(attention).json()["count"] == 1
    assert mutate(admin, item, "READY", "DELIVERING").status_code == 200
    assert admin.get(attention).json()["count"] == 1
    assert pin_client().get(attention).json()["count"] == 0  # Claimed by a different employee.
    assert mutate(admin, item, "DELIVERING", "DELIVERED").status_code == 200
    assert admin.get(attention).json()["count"] == 0
    _, _, second = session_item(identity_data[1], catalog_data[3], "READY")
    assert admin.get(attention).json()["count"] == 1
    assert mutate(admin, second, "READY", "DELIVERING").status_code == 200
    assert admin.get(attention).json()["count"] == 1
    identity_data[1].permissions.remove(
        *identity_data[1].permissions.filter(code__in=["CLAIM_DELIVERY", "COMPLETE_DELIVERY"])
    )
    assert admin.get(attention).status_code == 403

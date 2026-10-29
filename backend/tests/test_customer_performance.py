"""Opt-in customer profiling; all fixtures live in the isolated test schema."""

import json
import os
import statistics
import time
from decimal import Decimal
from pathlib import Path

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.models import Product
from apps.catalog.views import popular_products
from apps.orders.models import OrderItem
from tests.test_access import customer
from tests.test_identity import post_with_csrf
from tests.test_orders import payload


@pytest.mark.skipif(not os.environ.get("TAPSERVE_CUSTOMER_PROFILE"), reason="Opt-in profiling")
def test_customer_profile(point_data, catalog_data):
    client = customer(point_data[1])
    assert (
        post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    original = OrderItem.objects.get()
    products = Product.objects.bulk_create(
        [
            Product(
                unit=point_data[0].unit,
                category=catalog_data[1],
                production_sector=catalog_data[2],
                name=f"Produto {index:03}",
                base_price=Decimal("10.10"),
            )
            for index in range(80)
        ]
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                batch_id=original.batch_id,
                product=product,
                sector=catalog_data[2],
                quantity=1,
                unit_price=Decimal("10.10"),
                line_total=Decimal("10.10"),
                snapshot={"name": product.name, "options": []},
            )
            for product in products
            for _ in range(20)
        ]
    )
    result = {}
    for name, path in {
        "menu": "/api/v1/public/menu/",
        "categories": "/api/v1/public/categories/",
        "session": "/api/v1/public/session/",
        "orders": "/api/v1/public/orders/",
    }.items():
        samples, counts = [], []
        for _ in range(10):
            start = time.perf_counter()
            with CaptureQueriesContext(connection) as queries:
                assert client.get(path).status_code == 200
            samples.append((time.perf_counter() - start) * 1000)
            counts.append(len(queries))
        result[name] = {"median_ms": round(statistics.median(samples), 2), "queries": counts}
    stage = os.environ["TAPSERVE_CUSTOMER_PROFILE"]
    assert stage in {"before", "after"}
    output = Path(__file__).resolve().parents[2] / ".local" / f"customer-profile-{stage}.json"
    result["volume"] = {"products": Product.objects.count(), "items": OrderItem.objects.count()}
    result["menu_plan"] = (
        popular_products(point_data[0].unit, catalog_data[0])
        .order_by("-ordered_quantity", "category__position", "name", "id")[:20]
        .explain(analyze=True, buffers=True)
    )
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

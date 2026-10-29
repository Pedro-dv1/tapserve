"""Real PostgreSQL contracts used by the reconstructed customer surfaces."""

import uuid

from apps.catalog.models import Product
from apps.orders.models import OrderBatch, OrderItem
from tests.test_access import customer
from tests.test_identity import post_with_csrf
from tests.test_orders import payload


def test_general_notes_are_bounded_durable_idempotent_and_separate(point_data, catalog_data):
    client = customer(point_data[1])
    body = {**payload(catalog_data), "notes": "Trazer todos os itens juntos"}
    response = post_with_csrf(client, "/api/v1/public/orders/", body)
    assert response.status_code == 201
    batch = response.json()["batch"]
    assert batch["notes"] == body["notes"]
    assert batch["items"][0]["notes"] == "Sem pimenta"
    assert OrderBatch.objects.get().notes == body["notes"]
    assert post_with_csrf(client, "/api/v1/public/orders/", body).json() == response.json()
    assert (
        client.get(f"/api/v1/public/order-receipts/{body['idempotency_key']}/").json()
        == response.json()
    )
    assert client.get("/api/v1/public/orders/").json()["results"][0]["notes"] == body["notes"]
    assert (
        post_with_csrf(
            client, "/api/v1/public/orders/", {**body, "notes": "Outro texto"}
        ).status_code
        == 409
    )
    for fields in ({"notes": "x" * 501}, {"fee": "0.01"}):
        assert (
            post_with_csrf(
                client,
                "/api/v1/public/orders/",
                {**body, "idempotency_key": str(uuid.uuid4()), **fields},
            ).status_code
            == 400
        )
    assert OrderBatch.objects.count() == 1


def test_menu_search_description_popularity_and_timezone_are_real(point_data, catalog_data):
    client = customer(point_data[1])
    product = catalog_data[3]
    Product.objects.filter(id=product.id).update(description="Ingredientes frescos")
    data = client.get("/api/v1/public/menu/?search=frescos").json()
    assert data["count"] == 1
    assert data["results"][0]["ordered_quantity"] == 0
    assert data["results"][0]["most_ordered"] is False
    assert client.get("/api/v1/public/menu/?search=inexistente").json()["count"] == 0
    assert (
        client.get("/api/v1/public/context/").json()["unit_timezone"] == point_data[0].unit.timezone
    )
    assert (
        post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    data = client.get("/api/v1/public/menu/").json()["results"][0]
    assert data["ordered_quantity"] == 2 and data["most_ordered"] is True
    detail = client.get(f"/api/v1/public/products/{product.id}/").json()
    assert detail["ordered_quantity"] == 2 and detail["most_ordered"] is True
    OrderItem.objects.update(status="CANCELLED")
    data = client.get("/api/v1/public/menu/").json()["results"][0]
    assert data["ordered_quantity"] == 0 and data["most_ordered"] is False

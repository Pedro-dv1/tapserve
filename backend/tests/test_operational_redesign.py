from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.access.models import ServicePoint
from apps.catalog.models import Category, Menu, Product, ProductionSector
from apps.orders.models import OrderBatch, OrderItem, ServiceSession, SessionPoint
from apps.orders.production import ProductionQuery
from tests.test_identity import owner_client, pin_client


def session_item(staff, product, state="READY", session_state="OPEN"):
    session = ServiceSession.objects.create(unit=staff.unit, status=session_state)
    point = ServicePoint.objects.create(
        unit=staff.unit,
        name=f"Mesa {session.id}",
        type="TABLE",
        number=ServicePoint.objects.filter(unit=staff.unit).count() + 1,
        token_digest=str(session.id),
        token_ciphertext=b"synthetic-unused",
    )
    SessionPoint.objects.create(point=point, session=session)
    batch = OrderBatch.objects.create(session=session, origin_session=session, staff=staff)
    item = OrderItem.objects.create(
        batch=batch,
        product=product,
        sector=product.production_sector,
        status=state,
        quantity=2,
        unit_price=Decimal("10.10"),
        line_total=Decimal("20.20"),
        snapshot={"name": "Lanche", "sector_name": "Cozinha", "options": []},
    )
    return session, point, item


@pytest.mark.django_db
def test_delivery_scope_states_permissions_and_constant_queries(identity_data, catalog_data):
    _, owner, waiter, other_staff, _ = identity_data
    product = catalog_data[3]
    _, point, item = session_item(owner, product)
    client = pin_client()
    with CaptureQueriesContext(connection) as queries:
        result = client.get("/api/v1/staff/deliveries/")
    assert result.status_code == 200
    row = result.json()["results"][0]
    assert row["id"] == str(item.id) and row["point_names"] == [point.label]
    initial_queries = len(queries)
    for _ in range(10):
        session_item(owner, product)
    session_item(owner, product, "NEW")
    session_item(owner, product, "DELIVERED")
    session_item(owner, product, session_state="CLOSED")
    foreign = other_staff[0]
    menu = Menu.objects.create(unit=foreign.unit, name="Foreign")
    category = Category.objects.create(menu=menu, name="Foreign")
    sector = ProductionSector.objects.create(unit=foreign.unit, name="Foreign")
    foreign_product = Product.objects.create(
        unit=foreign.unit,
        category=category,
        production_sector=sector,
        name="Foreign",
        base_price=Decimal("10.10"),
    )
    session_item(foreign, foreign_product)
    with CaptureQueriesContext(connection) as queries:
        result = client.get("/api/v1/staff/deliveries/")
    assert result.status_code == 200 and result.json()["count"] == 11
    assert len(queries) == initial_queries <= 12
    attention = client.get("/api/v1/staff/deliveries/?attention=true").json()
    assert attention["count"] == 11 and len(attention["results"]) == 1
    assert client.get("/api/v1/staff/deliveries/?status=DELIVERED").status_code == 400
    assert client.get("/api/v1/staff/deliveries/?unit_id=foreign").status_code == 400
    waiter.permissions.remove(
        *waiter.permissions.filter(code__in=["CLAIM_DELIVERY", "COMPLETE_DELIVERY"])
    )
    assert client.get("/api/v1/staff/deliveries/").status_code == 403
    assert Client().get("/api/v1/staff/deliveries/").status_code == 401


@pytest.mark.django_db
def test_operation_summary_search_never_multiplies_items(identity_data, catalog_data):
    owner = identity_data[1]
    session, point, item = session_item(owner, catalog_data[3])
    second_point = ServicePoint.objects.create(
        unit=owner.unit,
        name=point.name + " extra",
        type="TABLE",
        number=2,
        token_digest="second",
        token_ciphertext=b"synthetic-unused",
    )
    SessionPoint.objects.create(session=session, point=second_point)
    client = owner_client(identity_data)
    response = client.get("/api/v1/staff/operation/", {"search": point.name})
    assert response.status_code == 200 and response.json()["count"] == 1
    assert response.json()["results"][0]["item_counts"]["READY"] == 1
    assert response.json()["results"][0]["item_counts"]["NEW"] == 0
    assert client.get("/api/v1/staff/operation/?search=absent").json()["count"] == 0
    assert client.get("/api/v1/staff/operation/?company_id=foreign").status_code == 400
    assert client.get("/api/v1/staff/operation/?page=1001").status_code == 400


@pytest.mark.django_db
def test_management_search_filters_reject_unknown_input_and_keep_scope(
    identity_data, catalog_data, point_data
):
    client = owner_client(identity_data)
    product = catalog_data[3]
    product.available = False
    product.save(update_fields=["available"])
    assert client.get("/api/v1/admin/products/?available=false&active=true").json()["count"] == 1
    assert client.get("/api/v1/admin/products/?available=true").json()["count"] == 0
    assert client.get("/api/v1/admin/categories/?available=true").status_code == 400
    assert client.get("/api/v1/admin/products/?active=maybe").status_code == 400
    for path in ["products", "staff", "service-points"]:
        assert client.get(f"/api/v1/admin/{path}/?search=absent").json()["count"] == 0
        assert client.get(f"/api/v1/admin/{path}/?unit_id=foreign").status_code == 400
        assert client.get(f"/api/v1/admin/{path}/", {"search": "x" * 101}).status_code == 400
        assert pin_client().get(f"/api/v1/admin/{path}/").status_code == 403
    assert client.get("/api/v1/admin/staff/?search=Other").json()["count"] == 0
    assert client.get("/api/v1/admin/service-points/?search=Mesa").json()["count"] == 1


def test_production_list_parameters_are_bounded_and_strict():
    query = ProductionQuery(data={"page": "2"})
    assert query.is_valid() and query.validated_data["page"] == 2
    for value in [{"unit_id": "foreign"}, {"page": 0}, {"page": 1001}, {"sector": "invalid"}]:
        assert not ProductionQuery(data=value).is_valid()

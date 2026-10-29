"""Real HTTP cookies/CSRF and real PostgreSQL; no mocked order or pricing service."""

import json
import uuid
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pytest

from apps.orders.models import OrderBatch, ProductionAssignment, ServiceSession
from tests.test_orders import payload


@pytest.mark.django_db(transaction=True)
def test_customer_confirmation_appears_in_staff_operation_over_http(
    point_data, catalog_data, identity_data, live_server
):
    customer = build_opener(HTTPCookieProcessor(CookieJar()))
    staff = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(browser, path, body=None, *, csrf=True):
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
            if csrf:
                headers["X-CSRFToken"] = call(browser, "/api/v1/csrf/")[1]["csrf_token"]
        # Only the pytest-controlled live server receives these fixture credentials.
        request = Request(  # noqa: S310
            live_server.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            response = browser.open(request, timeout=10)
        except HTTPError as response_error:
            response = response_error
        with response:
            return response.status, json.loads(response.read())

    assert (
        call(customer, "/api/v1/public/access/", {"public_token": point_data[1]}, csrf=False)[0]
        == 403
    )
    assert call(customer, "/api/v1/public/access/", {"public_token": point_data[1]})[0] == 200
    assert ServiceSession.objects.count() == 0
    assert call(customer, "/api/v1/public/menu/")[1]["results"][0]["name"] == "Lanche"
    body = payload(catalog_data)
    status, receipt = call(customer, "/api/v1/public/orders/", body)
    assert status == 201 and receipt["batch"]["items"][0]["line_total"] == "24.70"
    assert call(customer, "/api/v1/public/orders/", body) == (201, receipt)
    assert OrderBatch.objects.count() == 1
    assert call(staff, "/api/v1/staff/operation/")[0] == 401
    assert (
        call(
            staff,
            "/api/v1/staff/password-login/",
            {
                "company": "company-a",
                "unit": "unit-a",
                "username": "owner",
                "password": identity_data[-1],
            },
        )[0]
        == 200
    )
    operation = call(staff, "/api/v1/staff/operation/")[1]
    assert operation["count"] == 1 and operation["results"][0]["points"][0]["name"] == "Mesa 07"
    session_id = operation["results"][0]["id"]
    assert (
        call(staff, f"/api/v1/staff/sessions/{session_id}/orders/")[1]["results"][0]["id"]
        == receipt["batch"]["id"]
    )
    assert call(customer, "/api/v1/public/session/participants/", {"display_name": "Ana"})[0] == 201
    assert {
        person["display_name"]
        for person in call(customer, "/api/v1/public/session/")[1]["session"]["participants"]
    } == {"Pedro", "Ana"}
    manual = {**payload(catalog_data), "point_id": str(point_data[0].id)}
    status, manual_receipt = call(staff, "/api/v1/staff/orders/", manual)
    assert status == 201
    assert call(staff, "/api/v1/staff/orders/", manual) == (201, manual_receipt)
    feed = call(staff, "/api/v1/staff/orders/?status=NEW")[1]
    assert feed["count"] == 2 and {row["origin"] for row in feed["results"]} == {
        "CUSTOMER",
        "MANUAL",
    }
    assert call(customer, "/api/v1/public/orders/")[1]["count"] == 2
    table = call(staff, "/api/v1/staff/tables/")[1]["results"][0]
    assert table["order_count"] == 2 and table["subtotal"] == "49.40"
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    assert call(staff, "/api/v1/staff/production/items/")[1]["count"] == 2
    status, cleaning = call(
        customer,
        "/api/v1/public/service-requests/",
        {"kind": "CLEANING", "idempotency_key": str(uuid.uuid4())},
    )
    assert status == 201
    assert call(staff, "/api/v1/staff/tables/?filter=CLEANING")[1]["count"] == 1
    for before, after in [("OPEN", "ASSIGNED"), ("ASSIGNED", "RESOLVED")]:
        assert (
            call(
                staff,
                f"/api/v1/staff/service-requests/{cleaning['id']}/status/",
                {"idempotency_key": str(uuid.uuid4()), "expected_status": before, "status": after},
            )[0]
            == 200
        )
    assert call(staff, "/api/v1/staff/tables/?filter=CLEANING")[1]["count"] == 0
    item = manual_receipt["batch"]["items"][0]
    assert (
        call(
            staff,
            f"/api/v1/staff/items/{item['id']}/cancel/",
            {"idempotency_key": str(uuid.uuid4()), "expected_version": item["version"]},
        )[0]
        == 200
    )
    table = call(staff, "/api/v1/staff/tables/")[1]["results"][0]
    assert (
        table["order_count"] == 2
        and table["active_order_count"] == 1
        and table["subtotal"] == "24.70"
    )

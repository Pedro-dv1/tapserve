"""Customer mutations, price history, scoped invalidation and conditional media."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from threading import Barrier

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, transaction
from PIL import Image

from apps.access.models import DeviceAccess
from apps.catalog.models import Option, Product
from apps.catalog.services import publish_catalog_change
from apps.identity.models import AuditEvent
from apps.orders.interventions import ItemEditInput, change_item
from apps.orders.models import (
    DomainEvent,
    OrderItem,
    ProductionAssignment,
    SelectedOption,
    ServiceSession,
    SessionParticipant,
)
from apps.orders.production import StatusInput
from apps.orders.realtime import Audience
from common.idempotency import Conflict
from tests.test_access import customer
from tests.test_identity import owner_client, post_with_csrf
from tests.test_interventions import command, edit
from tests.test_orders import payload
from tests.test_unit_branding import logo_media as logo_media


@pytest.mark.parametrize("reason", [None, "", "  Cliente desistiu  "])
def test_optional_cancel_reason_is_bounded_audited_and_idempotent(point_data, catalog_data, reason):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    url = f"/api/v1/public/items/{item.id}/cancel/"
    assert post_with_csrf(client, url, {**command(item), "reason": "x" * 301}).status_code == 400
    body = command(item)
    if reason is not None:
        body["reason"] = reason
    response = post_with_csrf(client, url, body)
    assert response.status_code == 200
    assert response.json()["chargeable_total"] == "0.00"
    assert post_with_csrf(client, url, body).json() == response.json()
    audit = AuditEvent.objects.get(action="ITEM_CANCEL")
    assert audit.reason == (reason or "").strip()
    assert audit.details["after"]["status"] == "CANCELLED"
    assert post_with_csrf(client, url, command(item)).status_code == 409
    refusal = StatusInput(
        data={"idempotency_key": uuid.uuid4(), "expected_status": "NEW", "status": "REJECTED"}
    )
    assert refusal.is_valid() and refusal.validated_data["reason"] == ""


def test_edit_participant_preserves_prices_options_and_history(
    point_data, catalog_data, identity_data
):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    original_option = SelectedOption.objects.get()
    original_participant = str(item.participant_id)
    people = [
        SessionParticipant.objects.create(session=item.batch.session, display_name=name)
        for name in ["João", "Maria"]
    ]
    Product.objects.filter(pk=item.product_id).update(base_price=Decimal("99.00"))
    base = {
        "quantity": 3,
        "option_ids": [str(catalog_data[5].id)],
        "notes": "",
        "participant_id": str(people[0].id),
    }
    response = edit(client, item, {**command(item), **base})
    assert response.status_code == 200
    assert response.json()["line_total"] == "37.05"
    assert response.json()["participant_name"] == "João"
    assert response.json()["notes"] == ""
    assert SelectedOption.objects.get().id == original_option.id
    audit = AuditEvent.objects.get(action="ITEM_EDIT")
    assert audit.details["before"]["participant_id"] == original_participant
    assert audit.details["after"]["participant_id"] == str(people[0].id)
    # Legacy clients omitting the new field retain attribution.
    legacy = {key: value for key, value in base.items() if key != "participant_id"}
    assert edit(client, item, {**command(item), **legacy}).json()["participant_id"] == str(
        people[0].id
    )
    assert (
        edit(client, item, {**command(item), **base, "participant_id": str(people[1].id)}).json()[
            "participant_name"
        ]
        == "Maria"
    )
    admin = owner_client(identity_data)
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    kds = admin.get("/api/v1/staff/production/items/").json()["results"][0]
    assert kds["participant_name"] == "Maria" and kds["quantity"] == 3 and kds["notes"] == ""
    assert (
        admin.get(f"/api/v1/staff/sessions/{item.batch.session_id}/orders/").json()["results"][0][
            "items"
        ][0]["line_total"]
        == "37.05"
    )
    assert DomainEvent.objects.filter(kind="ITEM_EDIT", session=item.batch.session).count() == 3
    assert (
        edit(client, item, {**command(item), **base, "participant_id": None}).json()[
            "participant_id"
        ]
        is None
    )
    alternate = Option.objects.create(
        group=catalog_data[4], name="Pequeno", additional_price=Decimal("1.00")
    )
    changed = edit(client, item, {**command(item), **legacy, "option_ids": [str(alternate.id)]})
    assert changed.status_code == 200 and changed.json()["unit_price"] == "100.00"


def test_edit_rejects_other_sessions_units_inactive_people_and_invalid_inputs(
    point_data, catalog_data, identity_data
):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item = OrderItem.objects.get()
    original_participant = item.participant_id
    sessions = [
        ServiceSession.objects.create(unit=unit)
        for unit in [identity_data[0], identity_data[3][0].unit, identity_data[3][1].unit]
    ]
    invalid = [
        SessionParticipant.objects.create(session=session, display_name="Foreign")
        for session in sessions
    ]
    invalid.append(
        SessionParticipant.objects.create(
            session=item.batch.session, display_name="Inactive", active=False
        )
    )
    base = {"quantity": 2, "notes": "", "option_ids": [str(catalog_data[5].id)]}
    for person in invalid:
        assert (
            edit(
                client, item, {**command(item), **base, "participant_id": str(person.id)}
            ).status_code
            == 400
        )
    for fields in [
        {"quantity": 0},
        {"quantity": 100},
        {"notes": "x" * 501},
        {"participant_id": "invalid"},
    ]:
        assert edit(client, item, {**command(item), **base, **fields}).status_code == 400
    item.refresh_from_db()
    assert item.version == 1 and item.participant_id == original_participant
    assert not AuditEvent.objects.filter(action="ITEM_EDIT").exists()


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_item_edits_have_one_winner(point_data, catalog_data):
    client = customer(point_data[1])
    post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data))
    item, device = OrderItem.objects.get(), DeviceAccess.objects.get()
    barrier = Barrier(2)

    def act(quantity):
        close_old_connections()
        body = ItemEditInput(
            data={
                "idempotency_key": str(uuid.uuid4()),
                "expected_version": item.version,
                "quantity": quantity,
                "notes": "",
                "option_ids": [str(catalog_data[5].id)],
            }
        )
        body.is_valid(raise_exception=True)
        barrier.wait(timeout=10)
        try:
            change_item(device, item.id, body.validated_data)
            return True
        except Conflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(act, [3, 4]))
    assert sorted(result) == [False, True]
    item.refresh_from_db()
    assert item.version == 2 and item.line_total == item.unit_price * item.quantity
    assert AuditEvent.objects.filter(action="ITEM_EDIT").count() == 1


def test_catalog_invalidation_is_point_scoped_and_rolled_back(
    point_data, catalog_data, identity_data
):
    event_count = DomainEvent.objects.count()
    with transaction.atomic():
        publish_catalog_change(identity_data[0])
        event = DomainEvent.objects.get(kind="CATALOG_CHANGED")
        audience = Audience(
            point_data[0].unit_id, "device", None, point_data[0].id, False, frozenset()
        )
        assert audience.permits(event)
        another_point = Audience(
            point_data[0].unit_id, "another-device", None, uuid.uuid4(), False, frozenset()
        )
        assert another_point.permits(event)
        event.kind = "ITEM_EDIT"
        assert not another_point.permits(event)
        event.kind = "CATALOG_CHANGED"
        foreign = Audience(
            identity_data[3][0].unit_id, "foreign", None, point_data[0].id, True, frozenset()
        )
        assert not foreign.permits(event)
        transaction.set_rollback(True)
    assert DomainEvent.objects.count() == event_count
    admin = owner_client(identity_data)
    csrf = admin.get("/api/v1/csrf/").json()["csrf_token"]
    response = admin.patch(
        f"/api/v1/admin/products/{catalog_data[3].id}/",
        {"available": False},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    assert DomainEvent.objects.get(kind="CATALOG_CHANGED").point_id == point_data[0].id
    assert customer(point_data[1]).get("/api/v1/public/menu/").json()["count"] == 0


def test_product_image_revalidation_rechecks_access_and_availability(
    point_data, catalog_data, identity_data, logo_media
):
    client, admin = customer(point_data[1]), owner_client(identity_data)
    raw = BytesIO()
    Image.new("RGB", (32, 24), "white").save(raw, format="PNG")
    url = f"/api/v1/admin/products/{catalog_data[3].id}/image/"
    csrf = admin.get("/api/v1/csrf/").json()["csrf_token"]
    assert (
        admin.post(
            url,
            {"image": SimpleUploadedFile("test.png", raw.getvalue(), content_type="image/png")},
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 200
    )
    public = f"/api/v1/public/products/{catalog_data[3].id}/image/"
    response = client.get(public)
    assert response.status_code == 200 and response["Cache-Control"] == "private, no-cache"
    etag = response["ETag"]
    assert b"".join(response.streaming_content)
    assert response.closed
    assert client.get(public, HTTP_IF_NONE_MATCH=etag).status_code == 304
    Product.objects.filter(id=catalog_data[3].id).update(available=False)
    assert client.get(public, HTTP_IF_NONE_MATCH=etag).status_code == 404
    from django.test import Client

    assert Client().get(public, HTTP_IF_NONE_MATCH=etag).status_code == 401

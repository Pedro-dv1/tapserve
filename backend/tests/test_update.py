import uuid
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, close_old_connections, transaction
from PIL import Image

from apps.access.models import ServicePoint
from apps.catalog.models import Category, Menu, Product
from apps.identity.authentication import StaffIdentity
from apps.identity.models import AuditEvent, Role, Staff
from apps.orders.interventions import StaffItemCancelInput, change_item
from apps.orders.models import ItemStatusEvent, OrderItem, ProductionAssignment, SessionParticipant
from apps.orders.production import StatusInput, transition
from common.idempotency import Conflict
from tests.test_access import customer
from tests.test_identity import owner_client, post_with_csrf
from tests.test_interventions import command
from tests.test_orders import payload
from tests.test_production import mutate, status_body


def ordered(point_data, catalog_data, identity_data):
    client = customer(point_data[1])
    assert (
        post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    ProductionAssignment.objects.create(staff=identity_data[1], sector=catalog_data[2])
    return client, owner_client(identity_data), OrderItem.objects.get()


def test_delivered_cannot_be_cancelled_by_customer_staff_or_direct_database(
    point_data, catalog_data, identity_data
):
    client, admin, item = ordered(point_data, catalog_data, identity_data)
    for old, new in zip(
        ["NEW", "ACCEPTED", "PREPARING", "READY", "DELIVERING"],
        ["ACCEPTED", "PREPARING", "READY", "DELIVERING", "DELIVERED"],
        strict=True,
    ):
        assert mutate(admin, item, old, new).status_code == 200
    body = command(item)
    assert (
        post_with_csrf(client, f"/api/v1/public/items/{item.id}/cancel/", body).status_code == 409
    )
    assert (
        post_with_csrf(
            admin, f"/api/v1/staff/items/{item.id}/cancel/", {**body, "reason": "Correção"}
        ).status_code
        == 409
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.filter(id=item.id).update(status="CANCELLED")
    item.refresh_from_db()
    assert item.status == "DELIVERED" and str(item.line_total) == "24.70"
    assert not AuditEvent.objects.filter(action="ITEM_CANCEL").exists()


def test_rejection_reason_is_bounded_audited_and_does_not_change_snapshot(
    point_data, catalog_data, identity_data
):
    client, admin, item = ordered(point_data, catalog_data, identity_data)
    url = f"/api/v1/staff/items/{item.id}/status/"
    body = status_body("NEW", "REJECTED")
    for extra in (
        {"reason": "x" * 301},
        {"reason": "Motivo", "unit_id": str(item.batch.session.unit_id)},
    ):
        assert post_with_csrf(admin, url, {**body, **extra}).status_code == 400
    body["reason"] = "Produto indisponível na cozinha"
    original = item.snapshot
    response = post_with_csrf(admin, url, body)
    assert response.status_code == 200 and response.json()["status"] == "REJECTED"
    assert response.json()["chargeable_total"] == "0.00"
    assert post_with_csrf(admin, url, body).json() == response.json()
    assert mutate(admin, item, "REJECTED", "ACCEPTED").status_code == 409
    assert AuditEvent.objects.get(action="ITEM_REJECTED").reason == body["reason"]
    assert ItemStatusEvent.objects.get(status="REJECTED").reason == body["reason"]
    item.refresh_from_db()
    assert item.snapshot == original and str(item.line_total) == "24.70"
    assert client.get("/api/v1/public/menu/").json()["results"][0]["ordered_quantity"] == 0
    assert (
        client.get("/api/v1/public/orders/").json()["results"][0]["items"][0]["can_customer_change"]
        is False
    )


@pytest.mark.parametrize("state", ["ACCEPTED", "PREPARING", "DELIVERED", "CANCELLED"])
def test_rejection_is_only_valid_for_new_items(state, point_data, catalog_data, identity_data):
    _, admin, item = ordered(point_data, catalog_data, identity_data)
    OrderItem.objects.filter(id=item.id).update(status=state)
    assert (
        post_with_csrf(
            admin,
            f"/api/v1/staff/items/{item.id}/status/",
            {**status_body(state, "REJECTED"), "reason": "Motivo"},
        ).status_code
        == 409
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("race", ["accept-reject", "deliver-cancel"])
def test_order_races_have_one_winner(race, point_data, catalog_data, identity_data):
    _, _, item = ordered(point_data, catalog_data, identity_data)
    actor = StaffIdentity(
        identity_data[1],
        True,
        frozenset(identity_data[1].permissions.values_list("code", flat=True)),
    )
    if race == "deliver-cancel":
        OrderItem.objects.filter(id=item.id).update(
            status="DELIVERING", delivered_by=identity_data[1]
        )
    item.refresh_from_db()
    barrier = Barrier(2)

    def act(action):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            if action == "cancel":
                data = StaffItemCancelInput(
                    data={
                        "idempotency_key": str(uuid.uuid4()),
                        "expected_version": item.version,
                        "reason": "Motivo",
                    }
                )
                data.is_valid(raise_exception=True)
                change_item(actor, item.id, data.validated_data, cancel=True, manual=True)
            else:
                data = StatusInput(
                    data={
                        **status_body(item.status, action),
                        **({"reason": "Motivo"} if action == "REJECTED" else {}),
                    }
                )
                data.is_valid(raise_exception=True)
                transition(actor, item.id, data.validated_data)
            return True
        except Conflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                act,
                ["ACCEPTED", "REJECTED"] if race == "accept-reject" else ["DELIVERED", "cancel"],
            )
        )
    assert results.count(True) == results.count(False) == 1
    item.refresh_from_db()
    assert item.status in (
        {"ACCEPTED", "REJECTED"} if race == "accept-reject" else {"DELIVERED", "CANCELLED"}
    )


def test_participant_removal_scoped_audited_and_history_is_preserved(
    point_data, catalog_data, identity_data
):
    client, _, item = ordered(point_data, catalog_data, identity_data)
    person = post_with_csrf(
        client, "/api/v1/public/session/participants/", {"display_name": "Nome errado"}
    ).json()
    token = client.get("/api/v1/csrf/").json()["csrf_token"]

    def remove(identifier, body=None):
        return client.delete(
            f"/api/v1/public/session/participants/{identifier}/",
            body or {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    assert (
        client.delete(
            f"/api/v1/public/session/participants/{person['id']}/",
            {},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert remove(person["id"], {"unit": "foreign"}).status_code == 400
    assert remove(uuid.uuid4()).status_code == 404
    assert remove(person["id"]).status_code == remove(person["id"]).status_code == 204
    assert not SessionParticipant.objects.get(id=person["id"]).active
    assert AuditEvent.objects.filter(action="PARTICIPANT_REMOVED").count() == 1
    assert remove(item.participant_id).status_code == 409
    assert SessionParticipant.objects.get(id=item.participant_id).active


def test_point_menu_isolation_for_menu_detail_quote_order_and_images(
    point_data, catalog_data, identity_data
):
    point = point_data[0]
    client = customer(point_data[1])
    assert (
        post_with_csrf(client, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    point.refresh_from_db()
    assert point.menu_id == catalog_data[0].id
    other = Menu.objects.create(unit=point.unit, name="Outro cardápio")
    category = Category.objects.create(menu=other, name="Outra categoria")
    product = Product.objects.create(
        unit=point.unit,
        name="Outro produto",
        category=category,
        production_sector=catalog_data[2],
        base_price="5.00",
    )
    assert client.get("/api/v1/public/menu/").json()["count"] == 1
    assert client.get(f"/api/v1/public/products/{product.id}/").status_code == 404
    assert client.get(f"/api/v1/public/products/{product.id}/image/").status_code == 404
    assert (
        post_with_csrf(
            client,
            "/api/v1/public/quote/",
            {"product_id": str(product.id), "quantity": 1, "option_ids": []},
        ).status_code
        == 400
    )
    body = payload(catalog_data)
    body["items"][0]["product_id"] = str(product.id)
    assert post_with_csrf(client, "/api/v1/public/orders/", body).status_code == 400
    admin = owner_client(identity_data)
    other_point = post_with_csrf(
        admin,
        "/api/v1/admin/service-points/",
        {
            "name": "Outro ponto",
            "type": "TABLE",
            "number": 20,
            "menu": str(other.id),
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert other_point.status_code == 201
    assert (
        post_with_csrf(
            admin,
            "/api/v1/staff/orders/",
            {
                "point_id": other_point.json()["id"],
                "idempotency_key": str(uuid.uuid4()),
                "items": [{"product_id": str(product.id), "quantity": 10, "option_ids": []}],
            },
        ).status_code
        == 201
    )
    assert (
        client.get(f"/api/v1/public/products/{catalog_data[3].id}/").json()["most_ordered"] is True
    )
    assert admin.get(f"/api/v1/admin/products/?menu={other.id}").json()["results"][0]["id"] == str(
        product.id
    )
    foreign = Menu.objects.create(unit=identity_data[3][0].unit, name="Estrangeiro")
    assert admin.get(f"/api/v1/admin/products/?menu={foreign.id}").status_code == 404
    with pytest.raises(IntegrityError), transaction.atomic():
        ServicePoint.objects.filter(id=point.id).update(menu=foreign)


def test_ambiguous_legacy_menu_fails_closed(point_data, catalog_data):
    Menu.objects.create(unit=point_data[0].unit, name="Segundo")
    client = customer(point_data[1])
    assert client.get("/api/v1/public/menu/").status_code == 400


def test_group_destination_and_option_group_are_required(catalog_data, identity_data):
    admin = owner_client(identity_data)
    assert (
        post_with_csrf(
            admin,
            "/api/v1/admin/option-groups/",
            {"name": "Sem produto", "selection_type": "SINGLE"},
        ).status_code
        == 400
    )
    assert post_with_csrf(admin, "/api/v1/admin/options/", {"name": "Sem grupo"}).status_code == 400


def test_combined_product_image_upload_retry_invalid_and_removal(
    catalog_data, identity_data, settings
):
    settings.MEDIA_ROOT = (
        Path(__file__).resolve().parents[2] / ".local" / ("update-media-" + uuid.uuid4().hex)
    )
    output = BytesIO()
    Image.new("RGB", (16, 16), "red").save(output, format="PNG")
    admin = owner_client(identity_data)
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    data = {
        "name": "Com foto",
        "description": "Teste",
        "category": str(catalog_data[1].id),
        "production_sector": str(catalog_data[2].id),
        "base_price": "3.15",
        "active": "true",
        "available": "true",
        "idempotency_key": str(uuid.uuid4()),
    }

    def upload(raw):
        return admin.post(
            "/api/v1/admin/products/",
            {
                **data,
                "image": SimpleUploadedFile("../../photo.svg", raw, content_type="image/svg+xml"),
            },
            HTTP_X_CSRFTOKEN=token,
        )

    assert upload(b'<svg onload="alert(1)"/>').status_code == 400
    assert not Product.objects.filter(name=data["name"]).exists()
    response = upload(output.getvalue() + b"padding" * 12000)
    assert response.status_code == 201 and response.json()["has_image"] is True
    assert upload(output.getvalue()).json() == response.json()
    assert Product.objects.filter(name=data["name"]).count() == 1
    product = Product.objects.get(id=response.json()["id"])
    old = product.image_key
    assert default_storage.exists(old) and ".." not in old
    with Image.open(default_storage.open(old)) as image:
        assert image.format == "WEBP"
    with transaction.atomic():
        changed = admin.patch(
            f"/api/v1/admin/products/{product.id}/",
            {"remove_image": True},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert changed.status_code == 200 and not changed.json()["has_image"]


def test_point_menu_assignment_rejects_foreign_menu_and_active_occupation(
    point_data, catalog_data, identity_data
):
    _, admin, _ = ordered(point_data, catalog_data, identity_data)
    point = point_data[0]
    menu = Menu.objects.create(unit=point.unit, name="Outro menu")
    foreign = Menu.objects.create(unit=identity_data[3][0].unit, name="Foreign")
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    url = f"/api/v1/admin/service-points/{point.id}/"
    assert (
        admin.patch(
            url,
            {"menu": str(menu.id), "reason": "Troca"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 409
    )
    data = {
        "name": "Novo ponto",
        "type": "TABLE",
        "number": 20,
        "idempotency_key": str(uuid.uuid4()),
        "menu": str(foreign.id),
    }
    assert post_with_csrf(admin, "/api/v1/admin/service-points/", data).status_code == 400
    assert (
        post_with_csrf(
            admin, "/api/v1/admin/service-points/", {**data, "menu": str(menu.id)}
        ).status_code
        == 201
    )
    # Managing points does not require granting permission to edit the menu.
    identity_data[1].permissions.remove(*identity_data[1].permissions.filter(code="MANAGE_MENU"))
    response = admin.get("/api/v1/admin/service-points/menu-options/")
    assert response.status_code == 200 and response.json()["count"] == 2
    assert admin.get(f"/api/v1/admin/service-points/menu-options/{foreign.id}/").status_code == 404


def test_upload_failure_rolls_back_product_and_cleans_its_file(
    catalog_data, identity_data, settings, monkeypatch
):
    settings.MEDIA_ROOT = (
        Path(__file__).resolve().parents[2] / ".local" / ("update-media-" + uuid.uuid4().hex)
    )
    output = BytesIO()
    Image.new("RGB", (16, 16), "red").save(output, format="PNG")
    admin = owner_client(identity_data)
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]

    def unavailable(**kwargs):
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(AuditEvent.objects, "create", unavailable)
    response = admin.post(
        "/api/v1/admin/products/",
        {
            "name": "Rollback image",
            "category": str(catalog_data[1].id),
            "production_sector": str(catalog_data[2].id),
            "base_price": "3.00",
            "image": SimpleUploadedFile("photo.png", output.getvalue(), content_type="image/png"),
        },
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 500
    assert not Product.objects.filter(name="Rollback image").exists()
    assert not list(settings.MEDIA_ROOT.rglob("*.webp"))


def test_menu_unit_selection_requires_own_membership_strong_auth_csrf_and_rotation(
    identity_data, settings
):
    from django.test import Client

    from tests.test_identity import pin_client

    admin = owner_client(identity_data)
    unit = identity_data[3][0].unit
    role = Role.objects.get(unit=unit, name="OWNER")
    membership = Staff.objects.create(
        unit=unit,
        role=role,
        name="Same owner",
        login_code="same-owner",
        user=identity_data[1].user,
        pin_hash=identity_data[1].pin_hash,
    )
    membership.permissions.set(role.suggested_permissions.all())
    url = "/api/v1/staff/units/"
    assert pin_client().get(url).status_code == 403
    response = admin.get(url)
    assert response.status_code == 200
    assert {row["unit_id"] for row in response.json()["results"]} == {
        str(identity_data[0].id),
        str(unit.id),
    }
    assert (
        admin.post(
            url, {"membership_id": str(membership.id)}, content_type="application/json"
        ).status_code
        == 403
    )
    assert (
        post_with_csrf(
            admin, url, {"membership_id": str(membership.id), "unit_id": str(unit.id)}
        ).status_code
        == 400
    )
    assert (
        post_with_csrf(admin, url, {"membership_id": str(identity_data[3][1].id)}).status_code
        == 404
    )
    previous_cookie = admin.cookies[settings.SESSION_COOKIE_NAME].value
    selected = post_with_csrf(admin, url, {"membership_id": str(membership.id)})
    assert selected.status_code == 200 and selected.json()["unit_id"] == str(unit.id)
    assert admin.get("/api/v1/staff/me/").json()["unit_id"] == str(unit.id)
    old = Client(enforce_csrf_checks=True)
    old.cookies[settings.SESSION_COOKIE_NAME] = previous_cookie
    assert old.get("/api/v1/staff/me/").status_code == 401
    assert AuditEvent.objects.get(action="STAFF_UNIT_SELECTED").unit_id == unit.id

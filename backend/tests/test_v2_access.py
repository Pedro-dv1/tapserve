from apps.identity.models import Permission, Role
from apps.orders.models import OrderItem, ProductionAssignment
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload
from tests.test_production import mutate


def test_manager_production_without_assignments_and_kitchen_explicit_scope(
    identity_data, point_data, catalog_data
):
    device = customer(point_data[1])
    assert (
        post_with_csrf(device, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    )
    admin = owner_client(identity_data)
    item = OrderItem.objects.get()
    assert admin.get("/api/v1/staff/production/items/").json()["count"] == 1
    assert mutate(admin, item, "NEW", "ACCEPTED").status_code == 200
    assert mutate(admin, item, "ACCEPTED", "PREPARING").status_code == 200
    assert (
        admin.get("/api/v1/staff/production/items/").json()["results"][0]["status"] == "PREPARING"
    )
    waiter = identity_data[2]
    waiter.role = Role.objects.get(unit=waiter.unit, name="KITCHEN")
    waiter.save(update_fields=["role"])
    waiter.permissions.add(Permission.objects.get(code="UPDATE_PRODUCTION_STATUS"))
    kitchen = pin_client()
    assert kitchen.get("/api/v1/staff/production/items/").json()["count"] == 0
    assert mutate(kitchen, item, "PREPARING", "READY").status_code == 403
    ProductionAssignment.objects.create(staff=waiter, sector=catalog_data[2])
    assert kitchen.get("/api/v1/staff/production/items/").json()["count"] == 1
    assert mutate(kitchen, item, "PREPARING", "READY").status_code == 200
    assert (
        device.get("/api/v1/public/orders/").json()["results"][0]["items"][0]["status"] == "READY"
    )
    identity_data[1].permissions.remove(Permission.objects.get(code="UPDATE_PRODUCTION_STATUS"))
    assert admin.get("/api/v1/staff/production/items/").status_code == 403
    for role_name in ("ADMIN", "MANAGER"):
        manager = identity_data[1]
        manager.role = Role.objects.get(unit=manager.unit, name=role_name)
        manager.save(update_fields=["role"])
        manager.permissions.set(manager.role.suggested_permissions.all())
        assert admin.get("/api/v1/staff/me/").json()["staff"]["role"] == role_name
        created = post_with_csrf(device, "/api/v1/public/orders/", payload(catalog_data))
        assert created.status_code == 201
        current = OrderItem.objects.get(id=created.json()["batch"]["items"][0]["id"])
        assert str(current.id) in {
            row["id"] for row in admin.get("/api/v1/staff/production/items/").json()["results"]
        }
        for before, after in [
            ("NEW", "ACCEPTED"),
            ("ACCEPTED", "PREPARING"),
            ("PREPARING", "READY"),
        ]:
            assert mutate(admin, current, before, after).status_code == 200


def test_waiter_cannot_use_management_even_with_forged_client_or_strong_grants(identity_data):
    admin = owner_client(identity_data)
    owner = identity_data[1]
    owner.role = Role.objects.get(unit=owner.unit, name="WAITER")
    owner.save(update_fields=["role"])
    for url in ["/api/v1/admin/staff/", "/api/v1/admin/products/", "/api/v1/admin/order-policy/"]:
        assert admin.get(url).status_code == 403

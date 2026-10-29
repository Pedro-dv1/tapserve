import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client
from django.utils import timezone
from rest_framework.exceptions import Throttled

from apps.identity.models import AuditEvent, Permission, RateBucket, Role, Staff
from apps.identity.services import rate_limit


def post_with_csrf(client, path, data):
    token = client.get("/api/v1/csrf/").json()["csrf_token"]
    return client.post(path, data, content_type="application/json", HTTP_X_CSRFTOKEN=token)


def owner_client(data):
    client = Client(enforce_csrf_checks=True)
    result = post_with_csrf(
        client,
        "/api/v1/staff/password-login/",
        {"company": "company-a", "unit": "unit-a", "username": "owner", "password": data[-1]},
    )
    assert result.status_code == 200, result.content
    return client


def pin_client():
    client = Client(enforce_csrf_checks=True)
    response = post_with_csrf(
        client,
        "/api/v1/staff/login/",
        {"company": "company-a", "unit": "unit-a", "login_code": "waiter", "pin": "123456"},
    )
    assert response.status_code == 200, response.content
    return client


def test_pin_individual_login_and_logout(identity_data):
    client = pin_client()
    response = client.get("/api/v1/staff/me/")
    assert response.status_code == 200
    assert response.json()["auth_strength"] == "pin"
    assert response.json()["staff"]["id"] == str(identity_data[2].id)
    assert b"pin_hash" not in response.content and b"123456" not in response.content
    assert identity_data[2].pin_hash.startswith("argon2$")
    assert check_password("123456", identity_data[2].pin_hash)
    assert post_with_csrf(client, "/api/v1/staff/logout/", {}).status_code == 204
    assert client.get("/api/v1/staff/me/").status_code == 401
    assert AuditEvent.objects.filter(action="STAFF_LOGIN").count() == 1
    assert AuditEvent.objects.filter(action="STAFF_LOGOUT").count() == 1


def test_login_requires_csrf_even_when_anonymous(identity_data):
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post(
            "/api/v1/staff/login/", {"pin": "123456"}, content_type="application/json"
        ).status_code
        == 403
    )


def test_unknown_identity_and_wrong_pin_are_generic(identity_data):
    client = Client(enforce_csrf_checks=True)
    wrong = {"company": "company-a", "unit": "unit-a", "login_code": "waiter", "pin": "999999"}
    first = post_with_csrf(client, "/api/v1/staff/login/", wrong)
    second = post_with_csrf(client, "/api/v1/staff/login/", {**wrong, "login_code": "unknown"})
    assert first.status_code == second.status_code == 401
    assert first.json()["error"] == second.json()["error"]


def test_owner_requires_strong_auth_and_pin_cannot_manage(identity_data):
    client = Client(enforce_csrf_checks=True)
    assert (
        post_with_csrf(
            client,
            "/api/v1/staff/login/",
            {"company": "company-a", "unit": "unit-a", "login_code": "owner", "pin": "654321"},
        ).status_code
        == 401
    )
    waiter = identity_data[2]
    waiter.permissions.add(Permission.objects.get(code="MANAGE_STAFF"))
    client = pin_client()
    assert client.get("/api/v1/admin/staff/").status_code == 403
    assert post_with_csrf(client, "/api/v1/admin/staff/", {}).status_code == 403


def test_company_and_sibling_unit_are_scoped_in_every_staff_method(identity_data):
    client = owner_client(identity_data)
    response = client.get("/api/v1/admin/staff/")
    assert response.status_code == 200
    assert {row["id"] for row in response.json()["results"]} == {
        str(identity_data[1].id),
        str(identity_data[2].id),
    }
    for staff in identity_data[3]:
        endpoint = f"/api/v1/admin/staff/{staff.id}/"
        assert client.get(endpoint).status_code == 404
        token = client.get("/api/v1/csrf/").json()["csrf_token"]
        assert (
            client.patch(
                endpoint,
                {"active": False, "reason": "test"},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 404
        )
        assert (
            client.delete(
                endpoint, content_type="application/json", HTTP_X_CSRFTOKEN=token
            ).status_code
            == 404
        )
        staff.refresh_from_db()
        assert staff.active


def test_staff_creation_rejects_foreign_role_and_mass_assignment(identity_data):
    client = owner_client(identity_data)
    foreign_role = Role.objects.get(unit=identity_data[3][0].unit, name="WAITER")
    payload = {
        "name": "New waiter",
        "login_code": "new",
        "pin": "234567",
        "role_id": str(foreign_role.id),
        "permissions": ["VIEW_OPERATION"],
    }
    assert post_with_csrf(client, "/api/v1/admin/staff/", payload).status_code == 400
    role = Role.objects.get(unit=identity_data[0], name="WAITER")
    payload["role_id"] = str(role.id)
    for field in ("company_id", "unit_id", "user_id", "is_admin", "pin_hash", "credential_version"):
        assert (
            post_with_csrf(
                client, "/api/v1/admin/staff/", {**payload, field: "injected"}
            ).status_code
            == 400
        )
    response = post_with_csrf(client, "/api/v1/admin/staff/", payload)
    assert response.status_code == 201
    created = Staff.objects.get(id=response.json()["id"])
    assert created.unit_id == identity_data[0].id and check_password("234567", created.pin_hash)
    assert response.json()["permissions"] == ["VIEW_OPERATION"]


def test_disable_and_pin_reset_immediately_revoke_old_sessions(identity_data):
    waiter_client = pin_client()
    admin = owner_client(identity_data)
    target = identity_data[2]
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]
    response = admin.patch(
        f"/api/v1/admin/staff/{target.id}/",
        {"pin": "345678", "reason": "Individual PIN rotation"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    assert waiter_client.get("/api/v1/staff/me/").status_code == 401
    response = admin.patch(
        f"/api/v1/admin/staff/{target.id}/",
        {"active": False, "reason": "Disabled staff"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    target.refresh_from_db()
    assert not target.active and check_password("345678", target.pin_hash)


def test_idle_and_absolute_expiry(identity_data):
    import time

    client = pin_client()
    session = client.session
    session["tapserve_seen_at"] = int(time.time()) - 1801
    session.save()
    assert client.get("/api/v1/staff/me/").status_code == 401
    client = pin_client()
    session = client.session
    session["tapserve_issued_at"] = int(time.time()) - 28801
    session.save()
    assert client.get("/api/v1/staff/me/").status_code == 401


def test_database_blocks_cross_unit_roles_and_audit_mutation(identity_data):
    target = identity_data[2]
    foreign_role = Role.objects.get(unit=identity_data[3][0].unit, name="WAITER")
    with pytest.raises(IntegrityError), transaction.atomic():
        Staff.objects.filter(id=target.id).update(role=foreign_role)
    target.refresh_from_db()
    assert target.role.unit_id == target.unit_id
    event = AuditEvent.objects.create(unit=target.unit, staff=target, action="STAFF_UPDATED")
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditEvent.objects.filter(id=event.id).update(action="forged")
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditEvent.objects.filter(id=event.id).delete()
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditEvent.objects.create(
            unit=identity_data[3][0].unit, staff=target, action="STAFF_UPDATED"
        )
    assert AuditEvent.objects.filter(id=event.id, action="STAFF_UPDATED").exists()


def test_global_is_staff_does_not_create_tenant_membership(identity_data):
    password = secrets.token_urlsafe(32)
    get_user_model().objects.create_user(username="global", password=password, is_staff=True)
    client = Client(enforce_csrf_checks=True)
    response = post_with_csrf(
        client,
        "/api/v1/staff/password-login/",
        {"company": "company-a", "unit": "unit-a", "username": "global", "password": password},
    )
    assert response.status_code == 401
    assert client.get("/api/v1/admin/staff/").status_code == 401


@pytest.mark.django_db(transaction=True)
def test_pg_rate_limit_is_atomic_under_ten_simultaneous_attempts():
    barrier = Barrier(10)

    def attempt(_):
        close_old_connections()
        barrier.wait(timeout=10)
        try:
            rate_limit("concurrent-identity", 5)
            return True
        except Throttled:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(10)))
    assert results.count(True) == 5 and results.count(False) == 5


@pytest.mark.django_db
def test_rate_counter_saturates_and_expiry_cleanup_preserves_current_windows():
    for _ in range(30):
        try:
            rate_limit("bounded", 5, 60)
        except Throttled:
            pass
    bucket = RateBucket.objects.get()
    assert bucket.attempts == 6 and bucket.expires_at > timezone.now()
    RateBucket.objects.create(
        key="expired", window=1, attempts=1, expires_at=timezone.now() - timedelta(hours=13)
    )
    call_command("prune_rate_buckets", verbosity=0)
    assert RateBucket.objects.count() == 1 and RateBucket.objects.get().key == bucket.key

import secrets
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.access.models import DeviceAccess, ServicePoint
from apps.access.services import cipher, digest

LAN = "http://192.168.56.10:5173"
HOST = "127.0.0.1:8000"


@pytest.fixture
def lan_settings(settings):
    settings.ALLOWED_HOSTS = ["127.0.0.1", "192.168.56.10"]
    settings.CSRF_TRUSTED_ORIGINS = [LAN, "http://127.0.0.1:5173"]


def access(client, token, origin=LAN):
    response = client.get("/api/v1/csrf/", HTTP_HOST=HOST)
    return client.post(
        "/api/v1/public/access/",
        {"public_token": token},
        content_type="application/json",
        HTTP_HOST=HOST,
        HTTP_ORIGIN=origin,
        HTTP_X_CSRFTOKEN=response.json()["csrf_token"],
    )


def test_lan_and_pc_use_same_point_database_with_separate_host_only_device_cookies(
    point_data, lan_settings
):
    phone, pc = Client(enforce_csrf_checks=True), Client(enforce_csrf_checks=True)
    first = access(phone, point_data[1])
    second = access(pc, point_data[1], "http://127.0.0.1:5173")
    assert first.status_code == second.status_code == 200
    assert first.json()["point"]["id"] == second.json()["point"]["id"] == str(point_data[0].id)
    assert first.json()["device_id"] != second.json()["device_id"]
    cookie = first.cookies["tapserve-device"]
    assert cookie["httponly"] and cookie["samesite"] == "Lax"
    assert not cookie["secure"] and not cookie["domain"]
    assert access(phone, point_data[1]).json()["device_id"] == first.json()["device_id"]
    assert DeviceAccess.objects.count() == 2
    assert phone.get("/api/v1/public/context/", HTTP_HOST=HOST).status_code == 200
    assert phone.get("/api/v1/admin/staff/", HTTP_HOST=HOST).status_code == 401


def test_untrusted_origin_and_missing_csrf_stay_forbidden(point_data, lan_settings):
    browser = Client(enforce_csrf_checks=True)
    assert access(browser, point_data[1], "http://192.168.56.11:5173").status_code == 403
    assert access(browser, point_data[1], "http://untrusted.example").status_code == 403
    assert (
        browser.post(
            "/api/v1/public/access/",
            {"public_token": point_data[1]},
            content_type="application/json",
            HTTP_HOST=HOST,
            HTTP_ORIGIN=LAN,
        ).status_code
        == 403
    )
    assert DeviceAccess.objects.count() == 0


@pytest.mark.parametrize("origin", ["http://192.168.100.7:5173", "http://192.168.103.104:5173"])
def test_both_mobile_origins_accept_csrf_without_trusting_other_hosts(point_data, settings, origin):
    settings.ALLOWED_HOSTS = ["127.0.0.1", "192.168.100.7", "192.168.103.104"]
    settings.CSRF_TRUSTED_ORIGINS = ["http://192.168.100.7:5173", "http://192.168.103.104:5173"]
    browser = Client(enforce_csrf_checks=True)
    assert access(browser, point_data[1], origin).status_code == 200
    assert access(browser, point_data[1], "http://192.168.103.105:5173").status_code == 403


@pytest.mark.parametrize(
    "field", ["token", "active", "access_enabled", "unit", "company", "channels"]
)
def test_404_rejects_wrong_token_and_unavailable_points(point_data, lan_settings, field):
    point, token = point_data
    if field == "token":
        token = ("A" if token[0] != "A" else "B") + token[1:]
    elif field in {"active", "access_enabled"}:
        ServicePoint.objects.filter(id=point.id).update(**{field: False})
    elif field == "channels":
        ServicePoint.objects.filter(id=point.id).update(qr_enabled=False, nfc_enabled=False)
    else:
        obj = point.unit if field == "unit" else point.unit.company
        obj.active = False
        obj.save(update_fields=["active"])
    assert access(Client(enforce_csrf_checks=True), token).status_code == 404
    assert DeviceAccess.objects.count() == 0


def test_rotated_token_is_rejected_and_expired_or_revoked_devices_need_fresh_access(
    point_data, lan_settings
):
    point, token = point_data
    browser = Client(enforce_csrf_checks=True)
    assert access(browser, token).status_code == 200
    device = DeviceAccess.objects.get()
    DeviceAccess.objects.filter(id=device.id).update(
        issued_at=timezone.now() - timedelta(hours=13),
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert browser.get("/api/v1/public/context/", HTTP_HOST=HOST).status_code == 401
    assert access(browser, token).status_code == 200
    DeviceAccess.objects.filter(expires_at__gt=timezone.now()).update(revoked_at=timezone.now())
    assert browser.get("/api/v1/public/context/", HTTP_HOST=HOST).status_code == 401
    new_token = secrets.token_urlsafe(32)
    point.token_digest = digest(new_token)
    point.token_ciphertext = cipher().encrypt(new_token.encode())
    point.token_version += 1
    point.save(update_fields=["token_digest", "token_ciphertext", "token_version"])
    assert access(browser, token).status_code == 404
    assert access(browser, new_token).status_code == 200

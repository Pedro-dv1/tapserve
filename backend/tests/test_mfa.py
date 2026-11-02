import base64
import hashlib
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import close_old_connections
from django.test import Client
from django.utils import timezone

from apps.identity.mfa import token_cipher, totp
from apps.identity.models import AuditEvent, MfaChallenge, MfaCredential, PlatformOperator
from tests.test_identity import complete_mfa, owner_client, pin_client, post_with_csrf


def password_login(client, data):
    return post_with_csrf(client, "/api/v1/staff/password-login/", {
        "company": "company-a", "unit": "unit-a", "username": "owner", "password": data[-1]
    })


def enrollment_code(data):
    secret = parse_qs(urlsplit(data["provisioning_uri"]).query)["secret"][0]
    raw = base64.b32decode(secret + "=" * (-len(secret) % 8))
    return raw, totp(raw).generate(int(time.time())).decode()


def test_password_is_partial_until_real_totp_enrollment_and_no_seed_leak(identity_data):
    client = Client(enforce_csrf_checks=True)
    response = password_login(client, identity_data)
    assert response.status_code == 200
    assert response.json()["enrollment_required"] is True
    assert "_auth_user_id" not in client.session and "tapserve_staff_id" not in client.session
    for path in ("/api/v1/staff/me/", "/api/v1/admin/staff/", "/api/v1/staff/tables/"):
        assert client.get(path).status_code == 401
    raw, code = enrollment_code(response.json())
    challenge = MfaChallenge.objects.get()
    assert raw not in bytes(challenge.secret_ciphertext)
    assert token_cipher().decrypt(bytes(challenge.secret_ciphertext)) == raw
    completed = post_with_csrf(client, "/api/v1/staff/mfa/challenge/", {"code": code})
    assert completed.status_code == 200
    codes = completed.json()["recovery_codes"]
    assert len(codes) == len(set(codes)) == 10
    credential = MfaCredential.objects.get()
    assert credential.confirmed_at and credential.last_counter >= 0
    assert credential.recovery_hashes == [hashlib.sha256(value.encode()).hexdigest() for value in codes]
    assert not any(value in str(credential.recovery_hashes) for value in codes)
    assert client.get("/api/v1/staff/me/").status_code == 200
    challenge.refresh_from_db()
    assert challenge.used_at and bytes(challenge.secret_ciphertext) == b""
    assert AuditEvent.objects.filter(action="MFA_ENROLLED").count() == 1
    details = str(list(AuditEvent.objects.values_list("details", flat=True)))
    assert code not in details and raw.hex() not in details


def test_totp_replay_and_recovery_reuse_are_rejected(identity_data):
    original = Client(enforce_csrf_checks=True)
    response = password_login(original, identity_data)
    _, code = enrollment_code(response.json())
    completed = post_with_csrf(original, "/api/v1/staff/mfa/challenge/", {"code": code})
    recovery = completed.json()["recovery_codes"][0]
    first = Client(enforce_csrf_checks=True)
    assert password_login(first, identity_data).json()["enrollment_required"] is False
    assert post_with_csrf(first, "/api/v1/staff/mfa/challenge/", {"code": code}).status_code == 401
    assert post_with_csrf(first, "/api/v1/staff/mfa/challenge/", {"code": recovery}).status_code == 200
    second = Client(enforce_csrf_checks=True)
    password_login(second, identity_data)
    assert post_with_csrf(second, "/api/v1/staff/mfa/challenge/", {"code": recovery}).status_code == 401
    assert second.get("/api/v1/staff/me/").status_code == 401
    assert AuditEvent.objects.filter(action="MFA_RECOVERY_USED").count() == 1


def test_mfa_challenges_expire_and_password_changes_invalidate_them(identity_data):
    first = Client(enforce_csrf_checks=True)
    response = password_login(first, identity_data)
    _, code = enrollment_code(response.json())
    MfaChallenge.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert post_with_csrf(first, "/api/v1/staff/mfa/challenge/", {"code": code}).status_code == 401
    second = Client(enforce_csrf_checks=True)
    response = password_login(second, identity_data)
    _, code = enrollment_code(response.json())
    user = identity_data[1].user
    user.set_password(secrets.token_urlsafe(32))
    user.save()
    assert post_with_csrf(second, "/api/v1/staff/mfa/challenge/", {"code": code}).status_code == 401


def test_mfa_replacement_revokes_other_sessions_only_after_new_factor_confirmed(identity_data):
    first = owner_client(identity_data)
    second = owner_client(identity_data)
    credential = MfaCredential.objects.get()
    old_version = credential.version
    from tests.test_identity import _mfa_recovery

    recovery = _mfa_recovery[(str(credential.user_id), credential.version)].pop()
    replacement = post_with_csrf(first, "/api/v1/staff/mfa/", {"password": identity_data[-1], "code": recovery})
    assert replacement.status_code == 200 and replacement.json()["enrollment_required"]
    assert first.get("/api/v1/staff/me/").status_code == 401
    assert second.get("/api/v1/staff/me/").status_code == 200
    _, code = enrollment_code(replacement.json())
    assert post_with_csrf(first, "/api/v1/staff/mfa/challenge/", {"code": code}).status_code == 200
    credential.refresh_from_db()
    assert credential.version == old_version + 1
    assert second.get("/api/v1/staff/me/").status_code == 401
    assert first.get("/api/v1/staff/me/").status_code == 200


def test_reset_requires_password_and_factor_then_forces_reenrollment(identity_data):
    client = owner_client(identity_data)
    credential = MfaCredential.objects.get()
    from tests.test_identity import _mfa_recovery

    recovery = _mfa_recovery[(str(credential.user_id), credential.version)].pop()
    token = client.get("/api/v1/csrf/").json()["csrf_token"]
    response = client.delete("/api/v1/staff/mfa/", {"password": "wrong", "code": recovery}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 401
    response = client.delete("/api/v1/staff/mfa/", {"password": identity_data[-1], "code": recovery}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200 and response.json()["enrollment_required"]
    assert client.get("/api/v1/staff/me/").status_code == 401
    credential.refresh_from_db()
    assert credential.confirmed_at is None and not credential.recovery_hashes
    assert password_login(client, identity_data).json()["enrollment_required"] is True


def test_failed_mfa_attempts_persist_rate_limit_and_csrf_stays_required(identity_data):
    client = Client(enforce_csrf_checks=True)
    response = password_login(client, identity_data)
    raw, _ = enrollment_code(response.json())
    valid = {totp(raw).generate((int(time.time()) // 30 + offset) * 30).decode() for offset in (-1, 0, 1)}
    wrong = next(str(value).zfill(6) for value in range(10) if str(value).zfill(6) not in valid)
    assert client.post("/api/v1/staff/mfa/challenge/", {"code": wrong}, content_type="application/json").status_code == 403
    for _ in range(5):
        assert post_with_csrf(client, "/api/v1/staff/mfa/challenge/", {"code": wrong}).status_code == 401
    assert post_with_csrf(client, "/api/v1/staff/mfa/challenge/", {"code": wrong}).status_code == 429


def test_platform_mfa_is_separate_and_partial_session_has_no_global_access(identity_data):
    user = get_user_model().objects.create_user(username="platform-mfa", password=identity_data[-1])
    PlatformOperator.objects.create(user=user)
    client = Client(enforce_csrf_checks=True)
    response = post_with_csrf(client, "/api/v1/platform/login/", {"username": user.username, "password": identity_data[-1]})
    assert response.json()["mfa_required"] is True
    assert client.get("/api/v1/platform/companies/").status_code == 401
    assert client.get("/api/v1/staff/me/").status_code == 401
    _, code = enrollment_code(response.json())
    assert post_with_csrf(client, "/api/v1/staff/mfa/challenge/", {"code": code}).status_code == 401
    complete_mfa(client, response, realm="platform")
    assert client.get("/api/v1/platform/companies/").status_code == 200
    assert client.get("/api/v1/admin/staff/").status_code == 401


def test_pin_staff_cannot_manage_a_second_factor(identity_data):
    client = pin_client()
    assert client.get("/api/v1/staff/mfa/").status_code == 403
    assert post_with_csrf(client, "/api/v1/staff/mfa/", {"password": identity_data[-1], "code": "000000"}).status_code == 403


def test_offline_recovery_reauthenticates_and_revokes_existing_sessions(identity_data):
    client = owner_client(identity_data)
    output = StringIO()
    with patch("apps.identity.management.commands.reset_mfa.getpass.getpass", return_value=identity_data[-1]):
        call_command("reset_mfa", username="owner", reason="Identidade verificada pelo operador de infraestrutura", stdout=output)
    assert identity_data[-1] not in output.getvalue()
    assert client.get("/api/v1/staff/me/").status_code == 401
    assert password_login(client, identity_data).json()["enrollment_required"]


@pytest.mark.django_db(transaction=True)
def test_one_recovery_code_cannot_authenticate_two_concurrent_challenges(identity_data):
    initial = Client(enforce_csrf_checks=True)
    response = password_login(initial, identity_data)
    _, code = enrollment_code(response.json())
    recovery = post_with_csrf(initial, "/api/v1/staff/mfa/challenge/", {"code": code}).json()["recovery_codes"][0]
    clients = [Client(enforce_csrf_checks=True), Client(enforce_csrf_checks=True)]
    for client in clients:
        assert password_login(client, identity_data).status_code == 200
    barrier = Barrier(2)

    def finish(client):
        close_old_connections()
        barrier.wait(timeout=10)
        try:
            return post_with_csrf(client, "/api/v1/staff/mfa/challenge/", {"code": recovery}).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(finish, clients))
    assert sorted(outcomes) == [200, 401]

import json
import secrets
import uuid
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.access.models import DeviceAccess
from apps.access.services import cipher, digest
from apps.identity.models import AuditEvent, IdempotencyRecord, RateBucket
from apps.orders.models import DomainEvent, RealtimeLease, ServiceSession, SessionParticipant


def run_maintenance(**options):
    output = StringIO()
    call_command("maintain_data", stdout=output, **options)
    return json.loads(output.getvalue())


def expired_device(point, *, days=60):
    token = secrets.token_urlsafe(32)
    device = DeviceAccess.objects.create(
        point=point,
        token_digest=digest(token),
        token_ciphertext=cipher().encrypt(token.encode()),
        browser_digest=digest(secrets.token_urlsafe(32)),
        point_token_version=point.token_version,
        expires_at=timezone.now() + timedelta(hours=12),
    )
    DeviceAccess.objects.filter(id=device.id).update(
        issued_at=timezone.now() - timedelta(days=days + 1),
        expires_at=timezone.now() - timedelta(days=days),
    )
    device.refresh_from_db()
    return device


@pytest.mark.django_db
def test_maintenance_is_dry_run_and_preserves_historical_references(point_data):
    point = point_data[0]
    device = expired_device(point)
    audit = AuditEvent.objects.create(
        unit=point.unit, device=device, action="DEVICE_AUTHORIZED", resource_id=str(device.id)
    )
    Session.objects.create(
        session_key=secrets.token_hex(16), session_data="synthetic", expire_date=timezone.now()
    )
    RateBucket.objects.create(
        key=secrets.token_hex(32),
        window=0,
        attempts=1,
        expires_at=timezone.now() - timedelta(days=1),
    )
    RealtimeLease.objects.create(
        unit=point.unit,
        actor="D:" + str(device.id),
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    result = run_maintenance()
    assert result["mode"] == "dry-run"
    assert result["eligible"]["expired_device_credentials"] == 1
    assert result["eligible"]["expired_django_sessions"] == 1
    assert all(count == 0 for count in result["processed"].values())
    device.refresh_from_db()
    assert device.revoked_at is None and bytes(device.token_ciphertext)

    result = run_maintenance(apply=True, approved_policy="OPS-TEST-1")
    assert result["processed"]["expired_device_credentials"] == 1
    device.refresh_from_db()
    assert device.revoked_at and bytes(device.token_ciphertext) == b""
    assert device.browser_digest == ""
    assert AuditEvent.objects.get(id=audit.id).device_id == device.id
    assert DeviceAccess.objects.filter(id=device.id).exists()
    assert not Session.objects.exists()
    assert not RateBucket.objects.exists()
    assert not RealtimeLease.objects.exists()
    repeated = run_maintenance(apply=True, approved_policy="OPS-TEST-1")
    assert all(count == 0 for count in repeated["processed"].values())


@pytest.mark.django_db
def test_maintenance_keeps_active_credentials_and_bounds_batches(point_data):
    point = point_data[0]
    first, second = expired_device(point), expired_device(point)
    active = expired_device(point, days=-1)
    result = run_maintenance(apply=True, approved_policy="OPS-TEST-2", batch_size=1)
    assert result["processed"]["expired_device_credentials"] == 1
    assert (
        DeviceAccess.objects.filter(id__in=[first.id, second.id], revoked_at__isnull=False).count()
        == 1
    )
    active.refresh_from_db()
    assert active.revoked_at is None and bytes(active.token_ciphertext)


@pytest.mark.django_db
def test_replay_retention_requires_window_and_preserves_staff_results(point_data, identity_data):
    point = point_data[0]
    device = expired_device(point)
    DeviceAccess.objects.filter(id=device.id).update(revoked_at=timezone.now())
    records = []
    for actor, action in [(str(device.id), "ORDER"), (str(identity_data[1].id), "MANUAL_ORDER")]:
        record = IdempotencyRecord.objects.create(
            unit=point.unit,
            actor=actor,
            action=action,
            resource=str(point.id),
            key=uuid.uuid4(),
            request_digest=secrets.token_hex(32),
            response={},
            status=201,
        )
        IdempotencyRecord.objects.filter(id=record.id).update(
            created_at=timezone.now() - timedelta(days=60)
        )
        records.append(record)
    with pytest.raises(CommandError, match="retry-window"):
        run_maintenance(apply=True, approved_policy="OPS-TEST-3", replay_days=30)
    with pytest.raises(CommandError, match="retry-window"):
        run_maintenance(replay_days=5, retry_window_days=7)
    dry = run_maintenance(replay_days=30, retry_window_days=7)
    assert dry["eligible"]["expired_client_replays"] == 1
    assert IdempotencyRecord.objects.count() == 2
    run_maintenance(apply=True, approved_policy="OPS-TEST-3", replay_days=30, retry_window_days=7)
    assert not IdempotencyRecord.objects.filter(id=records[0].id).exists()
    assert IdempotencyRecord.objects.filter(id=records[1].id).exists()


@pytest.mark.django_db
def test_retention_does_not_remove_open_events_or_closed_operational_history(point_data):
    point = point_data[0]
    closed = ServiceSession.objects.create(
        unit=point.unit, status="CLOSED", closed_at=timezone.now() - timedelta(days=90)
    )
    active = ServiceSession.objects.create(unit=point.unit)
    participant = SessionParticipant.objects.create(session=closed, display_name="Synthetic person")
    old, live = [
        DomainEvent.objects.create(
            unit=point.unit, session=session, kind="ORDER_CREATED", version=1
        )
        for session in [closed, active]
    ]
    DomainEvent.objects.filter(id__in=[old.id, live.id]).update(
        created_at=timezone.now() - timedelta(days=90)
    )
    disabled = run_maintenance(apply=True, approved_policy="OPS-TEST-4")
    assert "domain_invalidations" not in disabled["eligible"]
    result = run_maintenance(
        apply=True, approved_policy="OPS-TEST-4", event_days=30, history_days=30
    )
    assert result["processed"]["domain_invalidations"] == 1
    assert result["history_eligible_for_policy_review"]["participants"] == 1
    assert DomainEvent.objects.filter(id=live.id).exists()
    assert ServiceSession.objects.filter(id=closed.id).exists()
    assert SessionParticipant.objects.get(id=participant.id).display_name == "Synthetic person"


@pytest.mark.parametrize(
    "options",
    [
        {"apply": True},
        {"apply": True, "approved_policy": "bad\nreference"},
        {"batch_size": 0},
        {"batch_size": 10001},
        {"event_days": 0},
        {"history_days": -1},
        {"replay_days": 36501},
    ],
)
def test_maintenance_rejects_unsafe_policy_before_querying_database(options):
    with pytest.raises(CommandError):
        run_maintenance(**options)


@pytest.mark.django_db
def test_expired_admission_and_mfa_cleanup_preserves_active_device(point_data, identity_data):
    from apps.access.models import DeviceAdmission
    from apps.identity.models import MfaChallenge

    point = point_data[0]
    active = expired_device(point, days=-1)
    old = timezone.now() - timedelta(hours=1)
    common = {"point": point, "point_token_version": point.token_version, "expires_at": old}
    expired = DeviceAdmission.objects.create(browser_digest=secrets.token_hex(32), **common)
    claimed = DeviceAdmission.objects.create(
        browser_digest=secrets.token_hex(32),
        device=active,
        status="APPROVED",
        decided_by=identity_data[1],
        **common,
    )
    challenge = MfaChallenge.objects.create(
        user=identity_data[1].user,
        staff=identity_data[1],
        realm="STAFF",
        credential_version=1,
        password_digest=secrets.token_hex(32),
        expires_at=old,
    )
    dry = run_maintenance()
    assert dry["eligible"]["expired_admission_bindings"] == 1
    assert MfaChallenge.objects.filter(id=challenge.id).exists()
    result = run_maintenance(apply=True, approved_policy="OPS-TEST-5")
    assert result["processed"]["expired_admission_bindings"] == 1
    assert result["processed"]["expired_mfa_challenges"] == 1
    expired.refresh_from_db()
    claimed.refresh_from_db()
    active.refresh_from_db()
    assert expired.status == "EXPIRED" and expired.browser_digest == ""
    assert claimed.status == "APPROVED" and claimed.browser_digest
    assert active.revoked_at is None
    assert not MfaChallenge.objects.filter(id=challenge.id).exists()
    repeated = run_maintenance(apply=True, approved_policy="OPS-TEST-5")
    assert all(count == 0 for count in repeated["processed"].values())

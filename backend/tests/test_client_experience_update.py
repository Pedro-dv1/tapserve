import asyncio
import json
import secrets
import shutil
import subprocess
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest
import qrcode
from channels.db import database_sync_to_async
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import timezone
from qrcode.image.svg import SvgPathFillImage

from apps.access.models import DeviceAccess, ServicePoint
from apps.access.services import cipher, connected_devices, digest, point_url
from apps.catalog.models import Product
from apps.catalog.video import validate_video
from apps.orders.models import RealtimeLease, ServiceRequest, ServiceSession, SessionPoint
from common.middleware import RequestBoundaryMiddleware
from tests.media import mp4_metadata
from tests.test_access import customer
from tests.test_identity import owner_client, pin_client, post_with_csrf
from tests.test_orders import payload
from tests.test_realtime import socket


@pytest.fixture
def workspace_media(settings, monkeypatch):
    root = Path(__file__).resolve().parents[2] / ".local"
    root.mkdir(exist_ok=True)
    directory = root / ("client-update-" + uuid.uuid4().hex)
    directory.mkdir()
    settings.MEDIA_ROOT = directory

    @contextmanager
    def probe_directory(**kwargs):
        # Windows sandbox cannot reopen tempfile's mode-0700 directories; files remain real.
        path = directory / ("probe-" + uuid.uuid4().hex)
        path.mkdir()
        try:
            yield str(path)
        finally:
            assert path.resolve().parent == directory.resolve()
            shutil.rmtree(path)

    monkeypatch.setattr("apps.catalog.video.TemporaryDirectory", probe_directory)
    try:
        yield directory
    finally:
        assert directory.resolve().parent == root.resolve()
        shutil.rmtree(directory)


def patch(client, path, data):
    token = client.get("/api/v1/csrf/").json()["csrf_token"]
    return client.patch(path, data, content_type="application/json", HTTP_X_CSRFTOKEN=token)


def test_configured_video_upload_limit_is_enforced_even_above_eight_digits(settings):
    settings.PRODUCT_VIDEO_MAX_BYTES = 100 * 1024 * 1024
    limit = settings.PRODUCT_VIDEO_MAX_BYTES + settings.PRODUCT_IMAGE_MAX_BYTES + 65536
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = limit
    middleware = RequestBoundaryMiddleware(lambda request: HttpResponse(status=200))
    factory = RequestFactory()
    for length, status in [(str(limit), 200), (str(limit + 1), 413), ("invalid", 413), ("-1", 413)]:
        # Exercise header rejection without allocating a 100 MiB request body.
        request = factory.generic(
            "HEAD",
            "/api/v1/admin/products/",
            data=b"x",
            content_type="multipart/form-data; boundary=test",
            CONTENT_LENGTH=length,
        )
        assert middleware(request).status_code == status


def test_identifier_rotation_disable_association_and_qr_preserve_session(
    point_data, catalog_data, identity_data, settings
):
    settings.PUBLIC_APP_ORIGIN = "https://atendimento.example.com"
    point, old_token = point_data
    admin = owner_client(identity_data)
    own = customer(old_token)
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    base = f"/api/v1/admin/service-points/{point.id}"
    original_session = ServiceSession.objects.get().id
    url = point_url(point)
    qr = admin.get(base + "/qr/")
    assert qr.status_code == 200
    assert qr.content == qrcode.make(url, image_factory=SvgPathFillImage).to_string()
    command = {
        "action": "ROTATE",
        "expected_version": 1,
        "reason": "Substituição",
        "confirmed": False,
    }
    assert post_with_csrf(admin, base + "/identifier/", command).status_code == 400
    command["confirmed"] = True
    assert post_with_csrf(admin, base + "/identifier/", command).status_code == 200
    assert post_with_csrf(admin, base + "/identifier/", command).status_code == 409
    point.refresh_from_db()
    assert point.token_version == 2 and point_url(point) != url
    new_token = point_url(point).rsplit("/", 1)[-1]
    assert (
        post_with_csrf(
            Client(enforce_csrf_checks=True), "/api/v1/public/access/", {"public_token": old_token}
        ).status_code
        == 404
    )
    assert own.get("/api/v1/public/context/").status_code == 200
    assert own.get("/api/v1/public/session/").json()["session"]["id"] == str(original_session)
    association = {
        "action": "ASSOCIATE",
        "expected_version": 2,
        "url": point_url(point),
        "reason": "QR existente",
    }
    assert post_with_csrf(admin, base + "/identifier/", association).status_code == 200
    for invalid in [
        url,
        point_url(point) + "?redirect=other",
        "https://evil.example/a/" + new_token,
    ]:
        assert (
            post_with_csrf(
                admin, base + "/identifier/", {**association, "url": invalid}
            ).status_code
            == 400
        )
    assert (
        patch(admin, base + "/", {"access_enabled": False, "reason": "Pausar entrada"}).status_code
        == 200
    )
    assert (
        post_with_csrf(
            Client(enforce_csrf_checks=True), "/api/v1/public/access/", {"public_token": new_token}
        ).status_code
        == 404
    )
    assert own.get("/api/v1/public/context/").status_code == 200
    assert (
        patch(admin, base + "/", {"access_enabled": True, "reason": "Reabrir entrada"}).status_code
        == 200
    )
    assert customer(new_token).get("/api/v1/public/session/").json()["session"]["id"] == str(
        original_session
    )
    assert ServiceSession.objects.count() == 1


def test_identifier_and_presence_permissions_are_scoped(point_data, identity_data):
    token = secrets.token_urlsafe(32)
    foreign = ServicePoint.objects.create(
        unit=identity_data[3][-1].unit,
        name="Foreign",
        type="TABLE",
        number=1,
        token_digest=digest(token),
        token_ciphertext=cipher().encrypt(token.encode()),
    )
    admin, waiter = owner_client(identity_data), pin_client()
    command = {
        "action": "ASSOCIATE",
        "url": point_url(foreign),
        "reason": "Teste",
        "expected_version": 1,
    }
    assert (
        post_with_csrf(
            admin, f"/api/v1/admin/service-points/{foreign.id}/identifier/", command
        ).status_code
        == 404
    )
    for suffix in ["url", "qr", "presence"]:
        assert admin.get(f"/api/v1/admin/service-points/{foreign.id}/{suffix}/").status_code == 404
        assert (
            waiter.get(f"/api/v1/admin/service-points/{point_data[0].id}/{suffix}/").status_code
            == 403
        )
    assert (
        post_with_csrf(
            waiter, f"/api/v1/admin/service-points/{point_data[0].id}/identifier/", command
        ).status_code
        == 403
    )


def test_check_request_uses_existing_queue_and_session_idempotently(
    point_data, catalog_data, identity_data
):
    own, second = customer(point_data[1]), customer(point_data[1])
    command = {"kind": "CHECK", "idempotency_key": str(uuid.uuid4())}
    assert post_with_csrf(own, "/api/v1/public/service-requests/", command).status_code == 400
    assert ServiceSession.objects.count() == 0
    assert (
        post_with_csrf(
            own,
            "/api/v1/public/service-requests/",
            {"kind": "ATTENDANT", "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 201
    )
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    response = post_with_csrf(own, "/api/v1/public/service-requests/", command)
    assert response.status_code == 201 and not response.json()["can_customer_cancel"]
    assert (
        post_with_csrf(own, "/api/v1/public/service-requests/", command).json() == response.json()
    )
    assert (
        post_with_csrf(
            second,
            "/api/v1/public/service-requests/",
            {**command, "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 409
    )
    session = ServiceSession.objects.get()
    assert session.status == "CHECK_REQUESTED" and session.check_requested_at is not None
    assert ServiceRequest.objects.filter(kind="CHECK").count() == 1
    call = response.json()["id"]
    assert (
        post_with_csrf(
            own,
            f"/api/v1/public/service-requests/{call}/cancel/",
            {"expected_status": "OPEN", "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 403
    )
    admin = owner_client(identity_data)
    assert any(
        row["kind"] == "CHECK"
        for row in admin.get("/api/v1/staff/service-requests/").json()["results"]
    )
    assert (
        post_with_csrf(
            admin,
            f"/api/v1/staff/service-requests/{call}/status/",
            {
                "expected_status": "OPEN",
                "status": "CANCELLED",
                "reason": "Cliente decidiu aguardar",
                "idempotency_key": str(uuid.uuid4()),
            },
        ).status_code
        == 200
    )
    session.refresh_from_db()
    assert session.status == "OPEN" and session.check_requested_at is None
    ServiceSession.objects.filter(id=session.id).update(status="CLOSED")
    assert (
        post_with_csrf(
            own,
            "/api/v1/public/service-requests/",
            {**command, "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 401
    )


def test_presence_counts_distinct_live_devices_and_excludes_stale_or_closed(
    point_data, catalog_data, identity_data
):
    own, second = customer(point_data[1]), customer(point_data[1])
    point = point_data[0]
    admin = owner_client(identity_data)
    endpoint = f"/api/v1/admin/service-points/{point.id}/presence/"
    assert admin.get(endpoint).json()["connected_devices"] == 0
    first = DeviceAccess.objects.get(token_digest=digest(own.cookies["tapserve-device"].value))
    DeviceAccess.objects.filter(id=first.id).update(last_seen_at=timezone.now())
    for _ in range(2):
        RealtimeLease.objects.create(
            unit=point.unit,
            actor="D:" + str(first.id),
            expires_at=timezone.now() + timedelta(seconds=30),
            acknowledged=True,
        )
    assert admin.get(endpoint).json()["connected_devices"] == 1
    second_device = DeviceAccess.objects.exclude(id=first.id).get()
    DeviceAccess.objects.filter(id=second_device.id).update(last_seen_at=timezone.now())
    RealtimeLease.objects.create(
        unit=point.unit,
        actor="D:" + str(second_device.id),
        expires_at=timezone.now() - timedelta(seconds=1),
        acknowledged=True,
    )
    assert connected_devices(point).count() == 1
    assert post_with_csrf(own, "/api/v1/public/orders/", payload(catalog_data)).status_code == 201
    assert connected_devices(point).count() == 1
    DeviceAccess.objects.filter(id=first.id).update(
        last_seen_at=timezone.now() - timedelta(seconds=31)
    )
    assert connected_devices(point).count() == 0
    DeviceAccess.objects.filter(id=first.id).update(last_seen_at=timezone.now())
    ServiceSession.objects.update(status="CLOSED")
    assert connected_devices(point).count() == 0
    assert second.get("/api/v1/public/context/").status_code == 401


def test_idle_authorization_releases_a_slot_without_evicting_live_device(point_data):
    for _ in range(5):
        customer(point_data[1])
    devices = list(DeviceAccess.objects.order_by("id"))
    old = timezone.now() - timedelta(minutes=6)
    DeviceAccess.objects.filter(id__in=[devices[0].id, devices[1].id]).update(
        issued_at=old, last_seen_at=old
    )
    RealtimeLease.objects.create(
        unit=point_data[0].unit,
        actor="D:" + str(devices[0].id),
        expires_at=timezone.now() + timedelta(seconds=30),
    )
    customer(point_data[1])
    devices[0].refresh_from_db()
    devices[1].refresh_from_db()
    assert devices[0].revoked_at is None and devices[1].revoked_at is not None
    assert DeviceAccess.objects.filter(revoked_at__isnull=True).count() == 5


def test_http_activity_keeps_a_slot_but_pending_socket_is_not_connected(point_data):
    clients = [customer(point_data[1]) for _ in range(5)]
    old = timezone.now() - timedelta(minutes=6)
    DeviceAccess.objects.update(issued_at=old, last_seen_at=old)
    device = DeviceAccess.objects.get(
        token_digest=digest(clients[0].cookies["tapserve-device"].value)
    )
    assert clients[0].get("/api/v1/public/context/").status_code == 200
    device.refresh_from_db()
    assert device.last_seen_at > old
    RealtimeLease.objects.create(
        unit=point_data[0].unit,
        actor="D:" + str(device.id),
        expires_at=timezone.now() + timedelta(seconds=30),
    )
    assert connected_devices(point_data[0]).count() == 0
    customer(point_data[1])
    device.refresh_from_db()
    assert device.revoked_at is None


def test_closed_session_authorizations_do_not_fill_the_next_service(point_data, catalog_data):
    clients = [customer(point_data[1]) for _ in range(5)]
    assert (
        post_with_csrf(clients[0], "/api/v1/public/orders/", payload(catalog_data)).status_code
        == 201
    )
    ServiceSession.objects.update(status="CLOSED")
    SessionPoint.objects.update(ended_at=timezone.now())
    fresh = customer(point_data[1])
    assert fresh.get("/api/v1/public/session/").json()["session"] is None
    assert connected_devices(point_data[0]).count() == 0
    assert clients[0].get("/api/v1/public/context/").status_code == 401
    assert (
        post_with_csrf(
            clients[0], "/api/v1/public/access/", {"public_token": point_data[1]}
        ).status_code
        == 200
    )
    assert clients[0].get("/api/v1/public/session/").json()["session"] is None


def test_video_content_validation_rejects_spoofs_oversize_and_missing_probe(
    settings, monkeypatch, workspace_media
):
    from rest_framework.exceptions import ValidationError

    for raw in [b'<svg onload="alert(1)"/>', b"not a movie"]:
        with pytest.raises(ValidationError):
            validate_video(SimpleUploadedFile("movie.mp4", raw, content_type="video/mp4"))
    settings.PRODUCT_VIDEO_MAX_BYTES = 4
    with pytest.raises(ValidationError):
        validate_video(SimpleUploadedFile("movie.mp4", b"12345"))
    settings.PRODUCT_VIDEO_MAX_BYTES = 1024
    raw = mp4_metadata()
    monkeypatch.setattr("apps.catalog.video.shutil.which", lambda _: "ffprobe")
    monkeypatch.setattr(
        "apps.catalog.video.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, b'{"streams":[]}'),
    )
    with pytest.raises(ValidationError):
        validate_video(SimpleUploadedFile("movie.mp4", raw))

    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("apps.catalog.video.subprocess.run", missing)
    monkeypatch.setattr("apps.catalog.video.shutil.which", lambda _: None)
    assert validate_video(SimpleUploadedFile("movie.mp4", raw)) == "mp4"


@pytest.mark.django_db(transaction=True)
def test_video_upload_retry_replace_remove_range_and_failed_write_cleanup(
    catalog_data, point_data, identity_data, settings, workspace_media, monkeypatch
):
    tmp_path = workspace_media
    probe_data = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "1.0"},
    }

    def probe(args, **kwargs):
        assert kwargs["timeout"] == 15 and "-enable_drefs" in args
        return subprocess.CompletedProcess(args, 0, json.dumps(probe_data).encode())

    monkeypatch.setattr("apps.catalog.video.shutil.which", lambda _: "ffprobe")
    monkeypatch.setattr("apps.catalog.video.subprocess.run", probe)
    admin, own = owner_client(identity_data), customer(point_data[1])
    key = str(uuid.uuid4())
    raw = mp4_metadata()
    product = catalog_data[3]
    endpoint = f"/api/v1/admin/products/{product.id}/"
    token = admin.get("/api/v1/csrf/").json()["csrf_token"]

    def upload(content, idempotency=key):
        body = encode_multipart(
            BOUNDARY,
            {
                "video": SimpleUploadedFile("../../movie.mp4", content),
                "idempotency_key": idempotency,
            },
        )
        return admin.patch(endpoint, body, content_type=MULTIPART_CONTENT, HTTP_X_CSRFTOKEN=token)

    assert upload(raw).status_code == 200
    product.refresh_from_db()
    first = product.video_key
    assert first and ".." not in first and default_storage.exists(first)
    assert upload(raw).status_code == 200
    assert len(list(tmp_path.rglob("*.mp4"))) == 1
    video_url = f"/api/v1/public/products/{product.id}/video/"
    response = own.get(video_url, HTTP_RANGE="bytes=4-11")
    assert response.status_code == 206 and b"".join(response.streaming_content) == raw[4:12]
    assert response["Content-Range"] == f"bytes 4-11/{len(raw)}"
    response = own.get(video_url, HTTP_RANGE="bytes=-8")
    assert b"".join(response.streaming_content) == raw[-8:]
    assert own.get(video_url, HTTP_RANGE="bytes=9999-").status_code == 416
    assert Client().get(video_url).status_code == 401
    assert upload(mp4_metadata(payload=b"changed"), str(uuid.uuid4())).status_code == 200
    product.refresh_from_db()
    assert product.video_key != first and not default_storage.exists(first)
    removed = product.video_key
    assert patch(admin, endpoint, {"remove_video": True}).json()["has_video"] is False
    assert not default_storage.exists(removed) and own.get(video_url).status_code == 404

    def fail(*args, **kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr("apps.catalog.services.AuditEvent.objects.create", fail)
    admin.raise_request_exception = False
    assert upload(raw, str(uuid.uuid4())).status_code == 500
    product.refresh_from_db()
    assert product.video_key == "" and not list(tmp_path.rglob("*.mp4"))
    assert Product.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_socket_acknowledgement_records_presence_and_disconnect_clears_it(point_data):
    own = customer(point_data[1])

    async def scenario():
        connection = socket(own, "/ws/v1/public/")
        try:
            assert (await connection.connect(timeout=10))[0]
            assert (await connection.receive_json_from(timeout=10))["kind"] == "SNAPSHOT_REQUIRED"
            assert (await connection.receive_json_from(timeout=10)) == {"type": "heartbeat"}
            await connection.send_json_to({"type": "heartbeat_ack"})
            # A subsequent heartbeat proves the previous acknowledgement was processed.
            assert (await connection.receive_json_from(timeout=10)) == {"type": "heartbeat"}
            assert (
                await database_sync_to_async(lambda: connected_devices(point_data[0]).count())()
                == 1
            )
        finally:
            await connection.disconnect()

    asyncio.run(scenario())
    assert connected_devices(point_data[0]).count() == 0

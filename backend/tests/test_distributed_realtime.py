"""Two actual ASGI processes share native PostgreSQL; no in-process broker substitute."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
from autobahn.asyncio.websocket import WebSocketClientFactory, WebSocketClientProtocol
from channels.db import database_sync_to_async
from django.db import connection

from tests.test_access import customer
from tests.test_identity import owner_client, post_with_csrf
from tests.test_orders import payload


class ProbeClient(WebSocketClientProtocol):
    def __init__(self):
        super().__init__()
        self.ready = asyncio.get_running_loop().create_future()
        self.messages = asyncio.Queue()

    def onOpen(self):
        self.ready.set_result(True)

    def onMessage(self, payload, isBinary):
        message = json.loads(payload)
        if message == {"type": "heartbeat"}:
            self.sendMessage(json.dumps({"type": "heartbeat_ack"}).encode())
            return
        self.messages.put_nowait(message)

    def onClose(self, wasClean, code, reason):
        if not self.ready.done():
            self.ready.set_exception(RuntimeError("WebSocket handshake refused"))
        self.messages.put_nowait(None)


@pytest.mark.django_db(transaction=True)
def test_committed_order_notifies_two_independent_native_asgi_processes(
    point_data, catalog_data, identity_data
):

    own, admin = customer(point_data[1]), owner_client(identity_data)
    processes = []
    logs = []
    ports = []
    root = Path(__file__).resolve().parents[2]
    log_directory = root / ".local"
    log_directory.mkdir(exist_ok=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_schema()")
        schema = cursor.fetchone()[0]
    assert schema.startswith("tapserve_test_") and len(schema) == 46
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.test",
        "TAPSERVE_TEST_SCHEMA": schema,
    }
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        for _ in range(2):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            ports.append(port)
            log = tempfile.TemporaryFile(mode="w+t", encoding="utf-8", dir=log_directory)
            logs.append(log)
            processes.append(
                # Fixed interpreter/module/loopback arguments, no shell or user command.
                subprocess.Popen(  # noqa: S603
                    [
                        sys.executable,
                        "-m",
                        "daphne",
                        "-b",
                        "127.0.0.1",
                        "-p",
                        str(port),
                        "-v",
                        "0",
                        "--websocket-max-message-size",
                        "256",
                        "--websocket-max-frame-size",
                        "256",
                        "config.asgi:application",
                    ],
                    cwd=root / "backend",
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    **options,
                )
            )  # noqa: S603
        assert processes[0].pid != processes[1].pid
        deadline = time.monotonic() + 20
        for port, process in zip(ports, processes, strict=True):
            while time.monotonic() < deadline:
                assert process.poll() is None, "Native ASGI process exited during startup"
                with socket.socket() as probe:
                    if probe.connect_ex(("127.0.0.1", port)) == 0:
                        break
                time.sleep(0.1)
            else:
                raise AssertionError("Native ASGI startup timed out")

        async def scenario():
            transports = []
            protocols = []
            try:
                for port, browser, path in ((ports[0], own, "public"), (ports[1], admin, "staff")):
                    cookie = "; ".join(
                        f"{name}={value.value}" for name, value in browser.cookies.items()
                    )
                    factory = WebSocketClientFactory(
                        f"ws://127.0.0.1:{port}/ws/v1/{path}/",
                        origin="http://testserver",
                        headers={"Cookie": cookie},
                    )
                    factory.protocol = ProbeClient
                    transport, protocol = await asyncio.get_running_loop().create_connection(
                        factory, "127.0.0.1", port
                    )
                    transports.append(transport)
                    protocols.append(protocol)
                    await asyncio.wait_for(protocol.ready, timeout=10)
                    assert (await asyncio.wait_for(protocol.messages.get(), timeout=10))[
                        "kind"
                    ] == "SNAPSHOT_REQUIRED"
                receipt = await database_sync_to_async(post_with_csrf)(
                    own, "/api/v1/public/orders/", payload(catalog_data)
                )
                assert receipt.status_code == 201
                first = await asyncio.wait_for(protocols[0].messages.get(), timeout=10)
                second = await asyncio.wait_for(protocols[1].messages.get(), timeout=10)
                assert first == second and first["kind"] == "ORDER_CREATED"
                assert first["event_id"] is not None and "token" not in json.dumps(first)
            finally:
                for protocol in protocols:
                    protocol.sendClose()
                for transport in transports:
                    transport.close()
                await asyncio.sleep(0.1)

        asyncio.run(scenario())
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            if sys.exc_info()[0] is not None:
                log.seek(0)
                print(log.read())
            log.close()

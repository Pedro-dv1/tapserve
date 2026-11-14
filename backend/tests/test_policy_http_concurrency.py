"""Two real HTTP editors cannot silently overwrite the same policy snapshot."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from apps.identity.models import AuditEvent
from tests.test_identity import owner_client


@pytest.mark.django_db(transaction=True)
def test_policy_http_conflict_preserves_winner_and_allows_explicit_rebase(identity_data, live_server):
    assert live_server.url.startswith(("http://localhost:", "http://127.0.0.1:"))
    clients = [owner_client(identity_data), owner_client(identity_data)]
    endpoint = live_server.url + "/api/v1/admin/order-policy/"
    headers = [{"Content-Type": "application/json", "X-CSRFToken": client.get("/api/v1/csrf/").json()["csrf_token"], "Cookie": "; ".join(f"{name}={item.value}" for name, item in client.cookies.items())} for client in clients]

    def send(index, body=None):
        request = Request(endpoint, headers=headers[index], method="GET" if body is None else "PUT", data=None if body is None else json.dumps(body).encode())  # noqa: S310 - pytest-owned loopback server only.
        try:
            response = urlopen(request, timeout=20)  # noqa: S310 - pytest-owned loopback server only.
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    snapshots = [send(index)[1] for index in range(2)]
    fields = ["table_takeaway_enabled", "leftover_packaging_enabled", "menu_layout"]
    bodies = [{"idempotency_key": str(uuid.uuid4()), "expected_window_minutes": snapshot["customer_edit_window_minutes"], "customer_edit_window_minutes": minutes, "expected_settings": {key: snapshot[key] for key in fields}, "reason": "Synthetic concurrent policy edit"} for snapshot, minutes in zip(snapshots, [20, 30], strict=True)]
    barrier = Barrier(2)

    def edit(index):
        barrier.wait(timeout=10)
        return send(index, bodies[index])

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(edit, range(2)))
    assert sorted(status for status, _ in responses) == [200, 409]
    winner = next(index for index, response in enumerate(responses) if response[0] == 200)
    loser = 1 - winner
    assert AuditEvent.objects.filter(action="ORDER_POLICY_UPDATED").count() == 1
    identity_data[0].refresh_from_db()
    assert identity_data[0].customer_edit_window_minutes == bodies[winner]["customer_edit_window_minutes"]
    current = send(loser)[1]
    retry = {**bodies[loser], "idempotency_key": str(uuid.uuid4()), "expected_window_minutes": current["customer_edit_window_minutes"], "expected_settings": {key: current[key] for key in fields}}
    status, saved = send(loser, retry)
    assert status == 200 and saved["customer_edit_window_minutes"] == bodies[loser]["customer_edit_window_minutes"]
    assert send(loser, retry) == (status, saved)
    assert AuditEvent.objects.filter(action="ORDER_POLICY_UPDATED").count() == 2
    identity_data[0].refresh_from_db()
    assert identity_data[0].customer_edit_window_minutes == bodies[loser]["customer_edit_window_minutes"]

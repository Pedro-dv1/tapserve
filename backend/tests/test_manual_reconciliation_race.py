"""A lost-response reconciliation races the same real manual-order request."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from django.db import close_old_connections

from apps.orders.models import OrderBatch, SessionPoint
from tests.test_identity import pin_client, post_with_csrf
from tests.test_orders import payload


@pytest.mark.django_db(transaction=True)
def test_abandon_and_late_manual_submission_serialize_without_duplicate(
    point_data, catalog_data
):
    browsers = [pin_client(), pin_client()]

    def send(index, body, receipt, barrier):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            path, command = (("/api/v1/staff/orders/", body) if index == 0 else
                (receipt, {"point": body["point_id"]}))
            response = post_with_csrf(browsers[index], path, command)
            return response.status_code, response.json()
        finally:
            close_old_connections()

    # The race plus both established outcomes must pass regardless of scheduling.
    for established in (None, "submit", "abandon"):
        session_id = SessionPoint.objects.filter(
            point=point_data[0], ended_at__isnull=True
        ).values_list("session_id", flat=True).first()
        body = {**payload(catalog_data), "point_id": str(point_data[0].id),
            "expected_session_id": str(session_id) if session_id else None}
        receipt = f"/api/v1/staff/manual-order-receipts/{body['idempotency_key']}/"
        initial_count = OrderBatch.objects.count()
        if established == "submit":
            assert post_with_csrf(browsers[0], "/api/v1/staff/orders/", body).status_code == 201
        elif established == "abandon":
            assert post_with_csrf(browsers[1], receipt, {"point": body["point_id"]}).json() == {"abandoned": True}
        barrier = Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(send, index, body, receipt, barrier) for index in range(2)]
            submitted, reconciled = [future.result() for future in futures]
        assert reconciled[0] == 200
        if submitted[0] == 201:
            assert established != "abandon"
            assert reconciled[1] == submitted[1]
            assert OrderBatch.objects.count() == initial_count + 1
        else:
            assert submitted[0] == 409 and established != "submit"
            assert reconciled[1] == {"abandoned": True}
            assert OrderBatch.objects.count() == initial_count
        before_retry = OrderBatch.objects.count()
        retry = post_with_csrf(browsers[0], "/api/v1/staff/orders/", body)
        assert retry.status_code == submitted[0]
        if retry.status_code == 201:
            assert retry.json() == submitted[1]
        else:
            assert retry.json()["error"] == submitted[1]["error"]
            # Error correlation belongs to each HTTP request, not the operation receipt.
            assert UUID(retry.json()["request_id"]) != UUID(submitted[1]["request_id"])
        assert OrderBatch.objects.count() == before_retry
        assert browsers[0].get(receipt + "?point=" + body["point_id"]).json() == reconciled[1]

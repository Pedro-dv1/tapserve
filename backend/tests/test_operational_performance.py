"""Opt-in reproducible profiling in the exclusively created PostgreSQL test schema."""

import json
import math
import os
import statistics
import time
from decimal import Decimal
from pathlib import Path

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.access.models import ServicePoint
from apps.catalog.models import Product
from apps.identity.models import AuditEvent
from apps.orders.models import (
    OrderBatch,
    OrderItem,
    ProductionAssignment,
    ServiceSession,
    SessionPoint,
)
from tests.test_identity import owner_client


@pytest.mark.skipif(not os.environ.get("TAPSERVE_PROFILE"), reason="Opt-in synthetic benchmark")
def test_operational_profile(identity_data, catalog_data):
    unit, owner = identity_data[:2]
    _, category, sector, product, _, _ = catalog_data
    ProductionAssignment.objects.create(staff=owner, sector=sector)
    Product.objects.bulk_create(
        [
            Product(
                unit=unit,
                category=category,
                production_sector=sector,
                name=f"Produto {i:04}",
                base_price=Decimal("10.10"),
            )
            for i in range(400)
        ]
    )
    sessions = ServiceSession.objects.bulk_create([ServiceSession(unit=unit) for _ in range(60)])
    points = ServicePoint.objects.bulk_create(
        [
            ServicePoint(
                unit=unit,
                name=f"Mesa {i:02}",
                type="TABLE",
                number=i + 1,
                token_digest=f"profile-{i}",
                token_ciphertext=b"synthetic-unused",
            )
            for i in range(60)
        ]
    )
    SessionPoint.objects.bulk_create(
        [SessionPoint(session=s, point=p) for s, p in zip(sessions, points, strict=True)]
    )
    batches = OrderBatch.objects.bulk_create(
        [OrderBatch(session=s, origin_session=s, staff=owner) for s in sessions for _ in range(20)]
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                batch=b,
                product=product,
                sector=sector,
                quantity=1,
                unit_price=Decimal("10.10"),
                line_total=Decimal("10.10"),
                snapshot={"name": "Lanche", "sector_name": "Cozinha", "options": []},
                status=["NEW", "PREPARING", "READY", "DELIVERED"][i % 4],
            )
            for b in batches
            for i in range(4)
        ]
    )
    AuditEvent.objects.bulk_create(
        [
            AuditEvent(unit=unit, staff=owner, action="PROFILE", resource_id=str(i))
            for i in range(3000)
        ]
    )
    client = owner_client(identity_data)
    paths = {
        "operation": "/api/v1/staff/operation/",
        "session_orders": f"/api/v1/staff/sessions/{sessions[0].id}/orders/",
        "production": "/api/v1/staff/production/items/",
        "products": "/api/v1/admin/products/",
        "staff": "/api/v1/admin/staff/",
        "calls": "/api/v1/staff/service-requests/",
    }
    if os.environ["TAPSERVE_PROFILE"] != "before":
        paths["deliveries"] = "/api/v1/staff/deliveries/"
    results = {}
    for name, path in paths.items():
        assert client.get(path).status_code == 200
        durations, counts, sql_times = [], [], []
        for _ in range(25):
            start = time.perf_counter()
            with CaptureQueriesContext(connection) as capture:
                response = client.get(path)
                assert response.status_code == 200
            durations.append((time.perf_counter() - start) * 1000)
            counts.append(len(capture))
            sql_times.append(sum(float(q["time"]) for q in capture.captured_queries) * 1000)
        results[name] = {
            "median_ms": round(statistics.median(durations), 3),
            "p95_ms": round(sorted(durations)[math.ceil(len(durations) * 0.95) - 1], 3),
            "queries": counts,
            "median_sql_ms": round(statistics.median(sql_times), 3),
        }
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version")
        version = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
        lock_waiters = cursor.fetchone()[0]
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_stat_statements')"
        )
        pg_stat_statements = cursor.fetchone()[0]
    root = Path(__file__).resolve().parents[2]
    output = root / ".local" / f"performance-{os.environ['TAPSERVE_PROFILE']}.json"
    assert os.environ["TAPSERVE_PROFILE"] in {"before", "after"}
    output.write_text(
        json.dumps(
            {
                "postgresql": version,
                "samples": 25,
                "lock_waiters": lock_waiters,
                "pg_stat_statements_installed": pg_stat_statements,
                "volume": {
                    "companies": 2,
                    "units": 3,
                    "products": 401,
                    "sessions": 60,
                    "batches": 1200,
                    "items": 4800,
                    "audit_events": 3000,
                },
                "endpoints": results,
                "operation_plan": ServiceSession.objects.filter(unit=unit, status="OPEN")
                .order_by("opened_at", "id")
                .explain(analyze=True, buffers=True),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(output.name, json.dumps(results))

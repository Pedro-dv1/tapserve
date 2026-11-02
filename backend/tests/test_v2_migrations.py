import secrets
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


@pytest.mark.django_db(transaction=True)
def test_admission_upgrade_revokes_legacy_capabilities_without_deleting_history():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [
        ("access", "0005_remove_servicepoint_point_unit_name_unique_and_more"),
        ("identity", "0010_mfa"),
        ("orders", "0015_external_receipts_and_session_lifecycle"),
        ("organizations", "0005_unit_menu_layout_unit_unit_menu_layout_valid"),
    ]
    try:
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        company = apps.get_model("organizations", "Company").objects.create(
            name="Synthetic upgrade", slug="synthetic-upgrade"
        )
        unit = apps.get_model("organizations", "Unit").objects.create(
            company=company, name="Synthetic", slug="synthetic"
        )
        point = apps.get_model("access", "ServicePoint").objects.create(
            unit=unit,
            name="Synthetic table",
            type="TABLE",
            number=1,
            token_digest=secrets.token_hex(32),
            token_ciphertext=b"synthetic",
        )
        session = apps.get_model("orders", "ServiceSession").objects.create(unit=unit)
        apps.get_model("orders", "SessionPoint").objects.create(point=point, session=session)
        device = apps.get_model("access", "DeviceAccess").objects.create(
            point=point,
            session=session,
            token_digest=secrets.token_hex(32),
            token_ciphertext=b"synthetic",
            browser_digest=secrets.token_hex(32),
            point_token_version=point.token_version,
            expires_at=timezone.now() + timedelta(hours=12),
        )
        participant = apps.get_model("orders", "SessionParticipant").objects.create(
            session=session, display_name="Synthetic participant"
        )
        MigrationExecutor(connection).migrate(latest)
        current = MigrationExecutor(connection).loader.project_state(latest).apps
        assert current.get_model("access", "DeviceAccess").objects.get(id=device.id).revoked_at
        assert (
            current.get_model("access", "ServicePoint").objects.get(id=point.id).token_digest
            == point.token_digest
        )
        assert (
            current.get_model("orders", "ServiceSession").objects.get(id=session.id).status
            == "OPEN"
        )
        assert (
            current.get_model("orders", "SessionParticipant")
            .objects.get(id=participant.id)
            .display_name
            == "Synthetic participant"
        )
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db(transaction=True)
def test_upgrade_and_reverse_preserve_legacy_order_history():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [
        ("orders", "0013_remove_servicerequest_request_kind_valid_and_more"),
        ("catalog", "0005_product_applied_option_groups_and_more"),
        ("organizations", "0003_unit_logo_key"),
    ]
    try:
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        company = apps.get_model("organizations", "Company").objects.create(
            name="Legacy", slug="legacy"
        )
        unit = apps.get_model("organizations", "Unit").objects.create(
            company=company, name="Legacy", slug="legacy"
        )
        role = apps.get_model("identity", "Role").objects.create(unit=unit, name="OWNER")
        staff = apps.get_model("identity", "Staff").objects.create(
            unit=unit, role=role, name="Legacy", login_code="legacy", pin_hash="!unusable"
        )
        menu = apps.get_model("catalog", "Menu").objects.create(unit=unit, name="Legacy")
        category = apps.get_model("catalog", "Category").objects.create(menu=menu, name="Legacy")
        sector = apps.get_model("catalog", "ProductionSector").objects.create(
            unit=unit, name="Legacy"
        )
        product = apps.get_model("catalog", "Product").objects.create(
            unit=unit,
            category=category,
            production_sector=sector,
            name="Legacy",
            base_price=Decimal("10.00"),
        )
        session = apps.get_model("orders", "ServiceSession").objects.create(
            unit=unit, status="CLOSED"
        )
        batch = apps.get_model("orders", "OrderBatch").objects.create(
            session=session, origin_session=session, staff=staff
        )
        snapshot = {"name": "Legacy", "unit_price": "10.00", "line_total": "20.00", "options": []}
        item = apps.get_model("orders", "OrderItem").objects.create(
            batch=batch,
            product=product,
            sector=sector,
            quantity=2,
            unit_price=Decimal("10.00"),
            line_total=Decimal("20.00"),
            snapshot=snapshot,
            status="DELIVERED",
        )
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        current = executor.loader.project_state(latest).apps
        migrated = current.get_model("orders", "OrderItem").objects.get(id=item.id)
        assert migrated.fulfillment_mode == "DINE_IN"
        assert migrated.snapshot == snapshot and migrated.status == "DELIVERED"
        assert migrated.line_total == Decimal("20.00")
        assert current.get_model("orders", "OrderBatch").objects.get(id=batch.id).channel == "STAFF"
        migrated_unit = current.get_model("organizations", "Unit").objects.get(id=unit.id)
        assert migrated_unit.menu_layout == "COMPACT"
        assert not migrated_unit.table_takeaway_enabled
        assert not migrated_unit.leftover_packaging_enabled
        assert not migrated_unit.public_pickup_enabled
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        old = executor.loader.project_state(previous).apps
        restored = old.get_model("orders", "OrderItem").objects.get(id=item.id)
        assert restored.snapshot == snapshot and restored.status == "DELIVERED"
        assert restored.line_total == Decimal("20.00")
    finally:
        MigrationExecutor(connection).migrate(latest)

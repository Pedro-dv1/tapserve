"""Run only in the disposable test database, never the persistent QA profile."""

import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.access.models import DeviceAdmission, ServicePoint
from apps.access.services import cipher
from apps.catalog.models import Category, Product
from apps.identity.models import AuditEvent, MfaCredential, Staff
from apps.orders.models import ExternalReceipt, OrderItem, ServiceSession, SessionLifecycleEvent
from apps.orders.settlement import session_totals
from apps.organizations.models import Company, Unit


@pytest.mark.django_db
def test_full_seed_is_additive_idempotent_and_preserves_real_domain_invariants(tmp_path):
    vault = tmp_path / "demo.enc"
    output = StringIO()
    with (
        patch("apps.orders.demo.validate_destination"),
        patch("apps.orders.demo.credential_path", return_value=vault),
    ):
        call_command("seed_environment", env="qa", stdout=output)
        assert Company.objects.count() == 2 and Unit.objects.count() == 3
        assert Staff.objects.count() == 23 and ServicePoint.objects.count() == 23
        assert Product.objects.count() == 56 and Category.objects.count() == 14
        assert ServiceSession.objects.count() == 16 and OrderItem.objects.count() == 22
        assert not MfaCredential.objects.exists()
        assert set(OrderItem.objects.values_list("status", flat=True)) >= {
            "NEW",
            "ACCEPTED",
            "PREPARING",
            "READY",
            "DELIVERED",
            "CANCELLED",
        }
        assert set(DeviceAdmission.objects.values_list("status", flat=True)) == {
            "PENDING",
            "APPROVED",
            "REVOKED",
        }
        assert ExternalReceipt.objects.count() == 6 and SessionLifecycleEvent.objects.count() == 2
        assert not AuditEvent.objects.filter(
            action__in=["DEMO_POINT_CREATED", "ENV_DEMO_SCENARIO"]
        ).exists()
        demo = ServicePoint.objects.get(name="Mesa Demo")
        assert not demo.session_links.exists() and not demo.device_accesses.exists()
        manifest = vault.with_name("seed-manifest.json")
        original_manifest = manifest.read_bytes()
        manifest.unlink()
        try:
            with pytest.raises(CommandError, match="no seed manifest"):
                call_command("seed_environment", env="qa", stdout=output)
        finally:
            manifest.write_bytes(original_manifest)
        for session in ServiceSession.objects.filter(status="CLOSED"):
            assert session_totals(session)[0] == session_totals(session)[1]
            assert not session.point_links.filter(ended_at__isnull=True).exists()
            assert not session.device_accesses.filter(revoked_at__isnull=True).exists()
        before = {
            model: list(model.objects.order_by("pk").values())
            for model in (
                Company,
                Unit,
                Staff,
                ServicePoint,
                Product,
                ServiceSession,
                OrderItem,
                AuditEvent,
            )
        }
        encrypted = vault.read_bytes()
        accounts = json.loads(cipher().decrypt(encrypted))
        waiter = Staff.objects.get(unit__slug="centro", login_code="demo-waiter")
        pin = accounts["a-centro:waiter"]["pin"]
        assert check_password(pin, waiter.pin_hash) and pin.encode() not in encrypted
        # A real operator edit must survive seed reruns along with tokens, hashes and histories.
        product = Product.objects.first()
        product.description = "Operator edit"
        product.name = "Operator renamed product"
        product.save(update_fields=["description", "name"])
        before[Product] = list(Product.objects.order_by("pk").values())
        call_command("seed_environment", env="qa", stdout=output)
        assert vault.read_bytes() == encrypted
        assert before == {model: list(model.objects.order_by("pk").values()) for model in before}
        assert pin not in output.getvalue()
        assert accounts["owner-a"]["password"] not in output.getvalue()
        with (
            patch("apps.orders.management.commands.verify_environment.validate_destination"),
            override_settings(
                PUBLIC_APP_ORIGIN="http://127.0.0.1", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1"]
            ),
        ):
            call_command("verify_environment", env="qa", stdout=output)
        assert before == {model: list(model.objects.order_by("pk").values()) for model in before}


@pytest.mark.django_db
def test_dry_run_rolls_back_records_and_never_writes_credentials_or_media(tmp_path):
    vault = tmp_path / "demo.enc"
    with (
        patch("apps.orders.demo.validate_destination"),
        patch("apps.orders.demo.credential_path", return_value=vault),
        patch("apps.orders.demo.save_image") as image,
    ):
        call_command("seed_environment", env="dev", dry_run=True, stdout=StringIO())
    assert not Company.objects.exists() and not AuditEvent.objects.exists()
    assert not vault.exists()
    image.assert_not_called()

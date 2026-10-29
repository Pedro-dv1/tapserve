import io
import secrets
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.access.models import ServicePoint
from apps.catalog.models import Product
from apps.identity.models import Staff


def test_demo_seed_refuses_non_dev_before_reading_any_credential():
    with patch("getpass.getpass") as prompt, pytest.raises(CommandError):
        call_command("seed_demo", username="demo-owner")
    prompt.assert_not_called()


@pytest.mark.django_db
@override_settings(DEBUG=True, SETTINGS_MODULE="config.settings.dev")
def test_demo_seed_creates_real_data_once_and_preserves_existing_credentials():
    password = secrets.token_urlsafe(32)
    stream = io.StringIO()
    with patch("getpass.getpass", side_effect=["123456", password, password, "654321"]):
        call_command("seed_demo", username="demo-owner", stdout=stream)
    assert (
        Product.objects.count() == 1
        and ServicePoint.objects.count() == 1
        and Staff.objects.count() == 2
    )
    original_hashes = list(Staff.objects.order_by("id").values_list("pin_hash", flat=True))
    with patch("getpass.getpass", side_effect=["234567", password, password, "765432"]):
        call_command("seed_demo", username="demo-owner", stdout=stream)
    assert (
        Product.objects.count() == 1
        and ServicePoint.objects.count() == 1
        and Staff.objects.count() == 2
    )
    assert list(Staff.objects.order_by("id").values_list("pin_hash", flat=True)) == original_hashes
    assert password not in stream.getvalue() and "123456" not in stream.getvalue()

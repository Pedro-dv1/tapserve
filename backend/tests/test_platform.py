import secrets
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction

from apps.identity.models import PlatformAuditEvent, PlatformOperator, Staff
from apps.organizations.models import Company, Unit
from tests.test_identity import owner_client, post_with_csrf


@pytest.mark.django_db
def test_platform_is_explicit_and_does_not_bypass_staff_scope(identity_data):
    client = owner_client(identity_data)
    assert client.get("/api/v1/platform/companies/").status_code == 401
    password = secrets.token_urlsafe(32)
    user = get_user_model().objects.create_user(
        username="platform", password=password, is_staff=True, is_superuser=True
    )
    assert (
        post_with_csrf(
            client, "/api/v1/platform/login/", {"username": "platform", "password": password}
        ).status_code
        == 401
    )
    operator = PlatformOperator.objects.create(user=user)
    assert (
        post_with_csrf(
            client, "/api/v1/platform/login/", {"username": "platform", "password": password}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/staff/me/").status_code == 401
    assert client.get("/api/v1/admin/staff/").status_code == 401
    created = post_with_csrf(
        client, "/api/v1/platform/companies/", {"name": "C", "slug": "company-c"}
    )
    assert created.status_code == 201
    unit = post_with_csrf(
        client,
        "/api/v1/platform/units/",
        {"name": "C unit", "slug": "unit-c", "company_id": created.json()["id"]},
    )
    assert unit.status_code == 201
    assert Unit.objects.get(id=unit.json()["id"]).roles.count() == 7
    assert (
        post_with_csrf(
            client,
            "/api/v1/platform/units/",
            {
                "name": "C unit",
                "slug": "unit-c",
                "company_id": created.json()["id"],
                "is_admin": True,
            },
        ).status_code
        == 400
    )
    event = PlatformAuditEvent.objects.get(action="COMPANY_CREATED")
    with pytest.raises(IntegrityError), transaction.atomic():
        PlatformAuditEvent.objects.filter(id=event.id).update(action="forged")
    operator.active = False
    operator.save()
    assert client.get("/api/v1/platform/me/").status_code == 401


@pytest.mark.django_db
def test_setup_commands_are_idempotent_and_never_output_credentials():
    password = secrets.token_urlsafe(32)
    arguments = dict(
        company="setup",
        company_name="Setup",
        unit="main",
        unit_name="Main",
        username="setup_owner",
        name="Owner",
    )
    output = StringIO()
    for _ in range(2):
        with patch(
            "apps.identity.management.commands.setup_unit.getpass.getpass",
            side_effect=[password, password, "765432"],
        ):
            call_command("setup_unit", **arguments, stdout=output)
    assert Company.objects.filter(slug="setup").count() == 1
    assert Unit.objects.count() == Staff.objects.count() == 1
    assert password not in output.getvalue() and "765432" not in output.getvalue()
    with patch(
        "apps.identity.management.commands.setup_platform.getpass.getpass",
        side_effect=[password, password],
    ):
        call_command("setup_platform", username="setup_owner", stdout=output)
    assert PlatformOperator.objects.count() == 1

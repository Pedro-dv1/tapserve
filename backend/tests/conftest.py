"""Isolate real PostgreSQL tests in a fresh schema without CREATEDB privileges."""

import secrets
import uuid
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.db import connections
from psycopg import sql

from apps.access.models import ServicePoint
from apps.access.services import cipher, digest
from apps.catalog.models import Category, Menu, Option, OptionGroup, Product, ProductionSector
from apps.identity.models import Role, Staff
from apps.identity.services import initialize_roles
from apps.organizations.models import Company, Unit


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    schema = "tapserve_test_" + uuid.uuid4().hex
    configuration = settings.DATABASES["default"]
    original_options = configuration["OPTIONS"].copy()
    database = connections["default"]
    with django_db_blocker.unblock():
        assert settings.SETTINGS_MODULE == "config.settings.test"
        assert database.vendor == "postgresql"
        database.close()
        with database.cursor() as cursor:
            # CREATE without IF NOT EXISTS proves this schema was created by this run.
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        database.close()
        configuration["OPTIONS"]["options"] = (
            original_options.get("options", "") + f" -c search_path={schema}"
        )
        try:
            call_command("migrate", verbosity=0, interactive=False)
            yield
        finally:
            connections.close_all()
            configuration["OPTIONS"] = original_options
            with database.cursor() as cursor:
                # Only the exclusively created run schema can be dropped; never public.
                assert schema.startswith("tapserve_test_") and len(schema) == 46
                cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
            database.close()


@pytest.fixture
def identity_data(db):
    company = Company.objects.create(name="Company A", slug="company-a")
    unit = Unit.objects.create(company=company, name="Unit A", slug="unit-a")
    other_unit = Unit.objects.create(company=company, name="Unit A2", slug="unit-a2")
    company_b = Company.objects.create(name="Company B", slug="company-b")
    unit_b = Unit.objects.create(company=company_b, name="Unit B", slug="unit-b")
    for current in (unit, other_unit, unit_b):
        initialize_roles(current)
    password = secrets.token_urlsafe(32)
    owner_user = get_user_model().objects.create_user(username="owner", password=password)
    owner_role = Role.objects.get(unit=unit, name="OWNER")
    owner = Staff.objects.create(
        unit=unit,
        role=owner_role,
        name="Owner",
        login_code="owner",
        pin_hash=make_password("654321", hasher="argon2"),
        user=owner_user,
    )
    owner.permissions.set(owner_role.suggested_permissions.all())
    waiter = Staff.objects.create(
        unit=unit,
        role=Role.objects.get(unit=unit, name="WAITER"),
        name="Waiter",
        login_code="waiter",
        pin_hash=make_password("123456", hasher="argon2"),
    )
    waiter.permissions.set(waiter.role.suggested_permissions.all())
    other_staff = [
        Staff.objects.create(
            unit=current,
            role=Role.objects.get(unit=current, name="WAITER"),
            name="Other waiter",
            login_code="waiter",
            pin_hash=make_password("123456", hasher="argon2"),
        )
        for current in (other_unit, unit_b)
    ]
    return unit, owner, waiter, other_staff, password


@pytest.fixture
def point_data(identity_data):
    token = secrets.token_urlsafe(32)
    point = ServicePoint.objects.create(
        unit=identity_data[0],
        name="Mesa 07",
        number=7,
        type="TABLE",
        token_digest=digest(token),
        token_ciphertext=cipher().encrypt(token.encode()),
    )
    return point, token


@pytest.fixture
def catalog_data(identity_data):
    unit = identity_data[0]
    menu = Menu.objects.create(unit=unit, name="Menu")
    category = Category.objects.create(menu=menu, name="Lanches")
    sector = ProductionSector.objects.create(unit=unit, name="Cozinha")
    product = Product.objects.create(
        unit=unit,
        name="Lanche",
        category=category,
        production_sector=sector,
        base_price=Decimal("10.10"),
    )
    group = OptionGroup.objects.create(
        product=product,
        name="Tamanho",
        selection_type="SINGLE",
        required=True,
        min_choices=1,
        max_choices=1,
    )
    product.applied_option_groups.add(group)
    option = Option.objects.create(group=group, name="Grande", additional_price=Decimal("2.25"))
    return menu, category, sector, product, group, option

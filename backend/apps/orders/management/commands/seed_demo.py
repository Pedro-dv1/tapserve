"""Explicit DEV-only data; all credentials come from hidden interactive input."""

import getpass
import re
import secrets
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.access.models import ServicePoint
from apps.access.services import cipher, digest
from apps.catalog.models import Category, Menu, Option, OptionGroup, Product, ProductionSector
from apps.identity.models import AuditEvent, Role, Staff
from apps.organizations.models import Unit


class Command(BaseCommand):
    help = "Seed an isolated demo company, owner, waiter, point and real menu; DEV only."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        if not settings.DEBUG or settings.SETTINGS_MODULE != "config.settings.dev":
            raise CommandError("Demo seed requires explicit DEV settings.")
        waiter_pin = getpass.getpass("PIN individual do garçom de demonstração (6–12 dígitos): ")
        if not re.fullmatch(r"[0-9]{6,12}", waiter_pin):
            raise CommandError("PIN inválido.")
        with transaction.atomic():
            call_command(
                "setup_unit",
                company="tapserve-demo",
                company_name="TapServe demonstração",
                unit="demo",
                unit_name="Unidade de demonstração",
                username=options["username"],
                name="Responsável de demonstração",
                role="OWNER",
                stdout=self.stdout,
            )
            unit = Unit.objects.select_for_update().get(company__slug="tapserve-demo", slug="demo")
            menu, _ = Menu.objects.get_or_create(unit=unit, name="Cardápio de demonstração")
            category, _ = Category.objects.get_or_create(menu=menu, name="Lanches")
            sector, _ = ProductionSector.objects.get_or_create(unit=unit, name="Cozinha")
            product, _ = Product.objects.get_or_create(
                unit=unit,
                name="Lanche de demonstração",
                defaults={
                    "category": category,
                    "production_sector": sector,
                    "base_price": Decimal("20.00"),
                    "description": "Produto para testar pedidos reais em DEV.",
                },
            )
            group, _ = OptionGroup.objects.get_or_create(
                product=product,
                name="Adicionais",
                defaults={"selection_type": "MULTIPLE", "max_choices": 2},
            )
            product.applied_option_groups.add(group)
            for name, price in (("Queijo", "3.00"), ("Bacon", "5.00")):
                Option.objects.get_or_create(
                    group=group, name=name, defaults={"additional_price": Decimal(price)}
                )
            token = secrets.token_urlsafe(32)
            ServicePoint.objects.get_or_create(
                unit=unit,
                name="Mesa demonstração",
                defaults={
                    "type": "TABLE",
                    "number": 1,
                    "token_digest": digest(token),
                    "token_ciphertext": cipher().encrypt(token.encode()),
                },
            )
            role = Role.objects.get(unit=unit, name="WAITER")
            waiter, created = Staff.objects.get_or_create(
                unit=unit,
                login_code="demo-waiter",
                defaults={
                    "role": role,
                    "name": "Garçom de demonstração",
                    "pin_hash": make_password(waiter_pin, hasher="argon2"),
                },
            )
            if created:
                waiter.permissions.set(role.suggested_permissions.all())
                AuditEvent.objects.create(unit=unit, action="DEMO_SEEDED", resource_id=str(unit.id))
        self.stdout.write(
            "Demonstração criada. Empresa: tapserve-demo; unidade: demo; garçom: demo-waiter. Credenciais existentes foram preservadas. Abra Pontos de atendimento para obter a URL/QR autorizado."
        )

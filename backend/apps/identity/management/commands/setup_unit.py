"""Interactive, idempotent first-unit setup without printing credentials."""

import getpass
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_slug
from django.db import transaction

from apps.identity.models import AuditEvent, Role, Staff
from apps.identity.permissions import ROLE_DEFAULTS
from apps.identity.services import initialize_roles
from apps.organizations.models import Company, Unit


class Command(BaseCommand):
    help = "Configure company/unit and strong owner; prompts hide the password and individual PIN."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True)
        parser.add_argument("--company-name", required=True)
        parser.add_argument("--unit", required=True)
        parser.add_argument("--unit-name", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--role", choices=list(ROLE_DEFAULTS), default="OWNER")
        parser.add_argument(
            "--refresh-role-grants",
            action="store_true",
            help="Explicitly replace this staff's grants with the current role template after credential verification.",
        )

    def handle(self, *args, **options):
        for key in ("company", "unit"):
            try:
                validate_slug(options[key])
            except ValidationError as error:
                raise CommandError("Company/unit codes must be valid slugs.") from error
            if len(options[key]) > 80:
                raise CommandError("Company/unit code is too long.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", options["username"]):
            raise CommandError("Username must have 1–32 letters/digits/_/-.")
        for key, maximum in (("company_name", 120), ("unit_name", 120), ("name", 100)):
            if not options[key].strip() or len(options[key]) > maximum:
                raise CommandError("Names must be nonempty and within their field limits.")
        password = getpass.getpass("Senha forte do responsável: ")
        if password != getpass.getpass("Confirme a senha: "):
            raise CommandError("Senhas diferentes.")
        pin = getpass.getpass("PIN individual do responsável (6–12 dígitos; gestão exige senha): ")
        if not re.fullmatch(r"[0-9]{6,12}", pin):
            raise CommandError("PIN inválido.")
        user_type = get_user_model()
        user = user_type.objects.filter(username=options["username"]).first()
        try:
            validate_password(password, user or user_type(username=options["username"]))
        except ValidationError as error:
            raise CommandError("A senha não atende à política de segurança.") from error
        if user is not None and (not user.is_active or not user.check_password(password)):
            raise CommandError("Credenciais inválidas para a identidade existente.")
        with transaction.atomic():
            company, _ = Company.objects.get_or_create(
                slug=options["company"], defaults={"name": options["company_name"]}
            )
            unit, _ = Unit.objects.get_or_create(
                company=company, slug=options["unit"], defaults={"name": options["unit_name"]}
            )
            if not company.active or not unit.active:
                raise CommandError("Empresa/unidade desativada.")
            initialize_roles(unit)
            if user is None:
                user = user_type.objects.create_user(
                    username=options["username"], password=password
                )
            role = Role.objects.get(unit=unit, name=options["role"])
            staff, created = Staff.objects.get_or_create(
                unit=unit,
                login_code=options["username"],
                defaults={
                    "user": user,
                    "role": role,
                    "name": options["name"],
                    "pin_hash": make_password(pin, hasher="argon2"),
                },
            )
            if staff.user_id != user.id or staff.role_id != role.id:
                raise CommandError("Identidade já vinculada; nenhuma credencial foi alterada.")
            if created or options["refresh_role_grants"]:
                staff.permissions.set(role.suggested_permissions.all())
                AuditEvent.objects.create(
                    unit=unit, staff=staff, action="UNIT_CONFIGURED", resource_id=str(unit.id)
                )
        self.stdout.write(
            "Empresa/unidade configurada. Credenciais não foram exibidas nem sobrescritas."
        )

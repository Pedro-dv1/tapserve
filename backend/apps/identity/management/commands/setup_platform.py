"""Explicitly create a SaaS operator using a strong hidden password."""

import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.identity.models import PlatformOperator


class Command(BaseCommand):
    help = "Create an explicit platform operator; is_staff is never sufficient."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        username = options["username"]
        if not username.strip() or len(username) > 150:
            raise CommandError("Usuário inválido.")
        password = getpass.getpass("Senha forte da plataforma: ")
        if password != getpass.getpass("Confirme a senha: "):
            raise CommandError("Senhas diferentes.")
        user_type = get_user_model()
        user = user_type.objects.filter(username=username).first()
        try:
            validate_password(password, user or user_type(username=username))
        except ValidationError as error:
            raise CommandError("Senha fora da política de segurança.") from error
        if user is not None and (not user.is_active or not user.check_password(password)):
            raise CommandError("Credenciais inválidas.")
        with transaction.atomic():
            if user is None:
                user = user_type.objects.create_user(username=username, password=password)
            PlatformOperator.objects.get_or_create(user=user)
        self.stdout.write("Operador configurado sem exibir ou alterar credenciais existentes.")

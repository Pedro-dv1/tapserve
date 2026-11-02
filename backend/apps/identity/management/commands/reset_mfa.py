"""Offline recovery requires trusted host access and verification of the account password."""

import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.identity.mfa import audit
from apps.identity.models import MfaChallenge, MfaCredential, Staff


class Command(BaseCommand):
    help = "Offline MFA recovery: reauthenticate password, revoke sessions, require new enrollment."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        reason = options["reason"].strip()
        if not reason or len(reason) > 300:
            raise CommandError("Informe um motivo de até 300 caracteres.")
        password = getpass.getpass("Senha da conta cuja identidade foi verificada: ")
        with transaction.atomic():
            user = get_user_model().objects.select_for_update().filter(
                username=options["username"], is_active=True
            ).first()
            if user is None or not user.check_password(password):
                raise CommandError("Credenciais inválidas; nenhum acesso foi alterado.")
            credential = MfaCredential.objects.select_for_update().filter(user=user).first()
            if credential is None:
                raise CommandError("A conta não possui configuração MFA; nenhuma alteração realizada.")
            credential.secret_ciphertext = b""
            credential.confirmed_at = None
            credential.last_counter = -1
            credential.recovery_hashes = []
            credential.version += 1
            credential.save()
            Staff.objects.filter(user=user).update(credential_version=F("credential_version") + 1)
            MfaChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
            memberships = list(Staff.objects.select_related("unit").filter(user=user))
            for staff in memberships:
                audit(user, "MFA_RESET_OFFLINE", staff=staff, reason=reason)
            if not memberships:
                audit(user, "MFA_RESET_OFFLINE")
        self.stdout.write("MFA redefinido. Sessões revogadas; novo cadastro obrigatório no próximo login privilegiado.")

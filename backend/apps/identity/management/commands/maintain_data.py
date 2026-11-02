"""Bounded, opt-in technical retention; operational history is never deleted."""

import json
import logging
import re
import uuid
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone

from apps.access.models import DeviceAccess, DeviceAdmission
from apps.identity.models import AuditEvent, IdempotencyRecord, MfaChallenge, RateBucket
from apps.orders.models import DomainEvent, RealtimeLease, ServiceSession, SessionParticipant

logger = logging.getLogger("tapserve.maintenance")


class Command(BaseCommand):
    help = "Report retention candidates; --apply requires an approved policy reference."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--apply", action="store_true")
        mode.add_argument("--dry-run", action="store_true")
        parser.add_argument("--approved-policy", default="")
        parser.add_argument("--batch-size", type=int, default=1000)
        parser.add_argument("--event-days", type=int)
        parser.add_argument("--replay-days", type=int)
        parser.add_argument("--retry-window-days", type=int)
        parser.add_argument("--history-days", type=int)

    def handle(self, *args, **options):
        apply = options["apply"]
        approval = options["approved_policy"]
        size = options["batch_size"]
        if not 1 <= size <= 10000:
            raise CommandError("batch-size must be between 1 and 10000")
        if apply and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{2,99}", approval):
            raise CommandError(
                "--apply requires --approved-policy with an approved ticket/reference"
            )
        for field in ("event_days", "replay_days", "retry_window_days", "history_days"):
            value = options[field]
            if value is not None and not 1 <= value <= 36500:
                raise CommandError("Retention and retry windows must be 1–36500 days")
        replay_days = options["replay_days"]
        retry_days = options["retry_window_days"]
        if replay_days is not None and (retry_days is None or replay_days < retry_days):
            raise CommandError("replay-days must cover an explicit --retry-window-days")

        now = timezone.now()
        devices = DeviceAccess.objects.filter(expires_at__lte=now).exclude(
            revoked_at__isnull=False, token_ciphertext=b"", browser_digest=""
        )
        queries: dict[str, models.QuerySet] = {
            "expired_device_credentials": devices,
            "expired_django_sessions": Session.objects.filter(expire_date__lte=now),
            "expired_rate_buckets": RateBucket.objects.filter(
                expires_at__lt=now - timedelta(hours=12)
            ),
            "expired_socket_leases": RealtimeLease.objects.filter(expires_at__lte=now),
            "expired_mfa_challenges": MfaChallenge.objects.filter(expires_at__lte=now),
            "expired_admission_bindings": DeviceAdmission.objects.filter(expires_at__lte=now)
            .filter(
                models.Q(device__isnull=True)
                | models.Q(device__expires_at__lte=now)
                | models.Q(device__revoked_at__isnull=False)
            )
            .exclude(browser_digest=""),
        }
        if options["event_days"] is not None:
            queries["domain_invalidations"] = DomainEvent.objects.filter(
                created_at__lt=now - timedelta(days=options["event_days"])
            ).filter(
                models.Q(session__isnull=True) | models.Q(session__status__in=["CLOSED", "MERGED"])
            )
        if replay_days is not None:
            cutoff = now - timedelta(days=replay_days)
            # ASVS V7/V14: only irrecoverably expired client actors lose retry results.
            expired_actors = DeviceAccess.objects.filter(expires_at__lt=cutoff).annotate(
                actor_id=Cast("id", models.CharField())
            )
            queries["expired_client_replays"] = IdempotencyRecord.objects.filter(
                created_at__lt=cutoff,
                action__in=["ORDER", "CALL_CREATE"],
                actor__in=expired_actors.values("actor_id"),
            )

        processed = dict.fromkeys(queries, 0)
        report = {
            "run_id": uuid.uuid4().hex,
            "mode": "apply" if apply else "dry-run",
            "policy_reference": approval or None,
            "batch_size": size,
            "policy_days": {
                "events": options["event_days"],
                "client_replays": replay_days,
                "retry_window": retry_days,
                "history_report_only": options["history_days"],
            },
            "eligible": {name: rows.count() for name, rows in queries.items()},
            "processed": processed,
            "history_action": "report_only; operational records, audit, staff and media preserved",
        }
        if options["history_days"] is not None:
            closed = ServiceSession.objects.filter(
                status__in=["CLOSED", "MERGED"],
                closed_at__lt=now - timedelta(days=options["history_days"]),
            )
            report["history_eligible_for_policy_review"] = {
                "closed_sessions": closed.count(),
                "participants": SessionParticipant.objects.filter(session__in=closed).count(),
                "unit_audit_events": AuditEvent.objects.filter(
                    created_at__lt=now - timedelta(days=options["history_days"])
                ).count(),
            }
        if apply:
            # ASVS V15.4: each bounded batch commits together; reruns are idempotent.
            with transaction.atomic():
                for name, rows in queries.items():
                    identifiers = list(
                        rows.select_for_update(of=("self",), skip_locked=True)
                        .order_by("pk")
                        .values_list("pk", flat=True)[:size]
                    )
                    selected = rows.filter(pk__in=identifiers)
                    if name == "expired_device_credentials":
                        count = selected.update(
                            revoked_at=Coalesce("revoked_at", now),
                            token_ciphertext=b"",
                            browser_digest="",
                        )
                    elif name == "expired_admission_bindings":
                        count = selected.update(status="EXPIRED", browser_digest="")
                    else:
                        count, _ = selected.delete()
                    processed[name] = count
            logger.info("maintenance_completed " + json.dumps(report, sort_keys=True))
        self.stdout.write(json.dumps(report, sort_keys=True))

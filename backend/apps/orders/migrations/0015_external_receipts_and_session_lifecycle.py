import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0014_remove_servicerequest_request_kind_valid_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExternalReceipt",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("MONEY", "Dinheiro"),
                            ("PIX", "Pix externo"),
                            ("CARD", "Cartão externo"),
                            ("OTHER", "Outro"),
                        ],
                        max_length=5,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=16)),
                ("notes", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "point",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="access.servicepoint"
                    ),
                ),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="identity.staff"
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="external_receipts",
                        to="orders.servicesession",
                    ),
                ),
                (
                    "reverses",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reversal",
                        to="orders.externalreceipt",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
                "indexes": [
                    models.Index(fields=["session", "created_at"], name="receipt_session_time_idx")
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(amount__gt=0), name="receipt_amount_positive"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(method__in=["MONEY", "PIX", "CARD", "OTHER"]),
                        name="receipt_method_valid",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SessionLifecycleEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[("CLOSE", "Fechar"), ("REOPEN", "Reabrir")], max_length=6
                    ),
                ),
                ("reason", models.CharField(max_length=300)),
                ("consumption_total", models.DecimalField(decimal_places=2, max_digits=16)),
                ("declared_received", models.DecimalField(decimal_places=2, max_digits=16)),
                ("version", models.PositiveIntegerField()),
                ("points", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lifecycle_events",
                        to="orders.servicesession",
                    ),
                ),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="identity.staff"
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(action__in=["CLOSE", "REOPEN"]),
                        name="lifecycle_action_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(consumption_total__gte=0, declared_received__gte=0),
                        name="lifecycle_totals_nonnegative",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            """
            CREATE FUNCTION tapserve_external_receipt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE scope_id uuid; receipt_state text; original orders_externalreceipt%ROWTYPE;
            BEGIN
              IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'External receipt declarations are append-only' USING ERRCODE='23514';
              END IF;
              SELECT unit_id, status INTO scope_id, receipt_state FROM orders_servicesession WHERE id=NEW.session_id;
              IF scope_id IS DISTINCT FROM (SELECT unit_id FROM identity_staff WHERE id=NEW.staff_id)
                 OR scope_id IS DISTINCT FROM (SELECT unit_id FROM access_servicepoint WHERE id=NEW.point_id)
                 OR NOT EXISTS (SELECT 1 FROM orders_sessionpoint WHERE session_id=NEW.session_id AND point_id=NEW.point_id)
                 OR receipt_state NOT IN ('OPEN', 'CHECK_REQUESTED', 'CLOSING', 'REOPENED') THEN
                RAISE EXCEPTION 'External receipt scope or state mismatch' USING ERRCODE='23514';
              END IF;
              IF NEW.reverses_id IS NOT NULL THEN
                SELECT * INTO original FROM orders_externalreceipt WHERE id=NEW.reverses_id;
                IF original.id IS NULL OR original.reverses_id IS NOT NULL
                   OR original.session_id IS DISTINCT FROM NEW.session_id
                   OR original.point_id IS DISTINCT FROM NEW.point_id
                   OR original.amount IS DISTINCT FROM NEW.amount
                   OR original.method IS DISTINCT FROM NEW.method THEN
                  RAISE EXCEPTION 'Invalid external receipt reversal' USING ERRCODE='23514';
                END IF;
              END IF;
              RETURN NEW;
            END; $$;
            CREATE TRIGGER external_receipt_guard BEFORE INSERT OR UPDATE OR DELETE ON orders_externalreceipt
              FOR EACH ROW EXECUTE FUNCTION tapserve_external_receipt_guard();
            CREATE FUNCTION tapserve_lifecycle_guard() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Session lifecycle is append-only' USING ERRCODE='23514';
              END IF;
              IF (SELECT unit_id FROM orders_servicesession WHERE id=NEW.session_id) IS DISTINCT FROM
                 (SELECT unit_id FROM identity_staff WHERE id=NEW.staff_id) THEN
                RAISE EXCEPTION 'Session lifecycle scope mismatch' USING ERRCODE='23514';
              END IF;
              RETURN NEW;
            END; $$;
            CREATE TRIGGER lifecycle_guard BEFORE INSERT OR UPDATE OR DELETE ON orders_sessionlifecycleevent
              FOR EACH ROW EXECUTE FUNCTION tapserve_lifecycle_guard();
            """,
            """
            DROP TRIGGER lifecycle_guard ON orders_sessionlifecycleevent;
            DROP FUNCTION tapserve_lifecycle_guard();
            DROP TRIGGER external_receipt_guard ON orders_externalreceipt;
            DROP FUNCTION tapserve_external_receipt_guard();
            """,
        ),
    ]

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def add_permissions(apps, schema_editor):
    permission = apps.get_model("identity", "Permission")
    role = apps.get_model("identity", "Role")
    for code, names in {
        "APPROVE_DEVICE_ACCESS": ["OWNER", "ADMIN", "MANAGER", "WAITER"],
        "CORRECT_RECEIPT": ["OWNER", "ADMIN"],
    }.items():
        grant, _ = permission.objects.get_or_create(code=code)
        for template in role.objects.filter(name__in=names):
            template.suggested_permissions.add(grant)
    # Existing effective staff grants are deliberately unchanged; provisioning is explicit.


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0009_staff_deleted_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="MfaCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("secret_ciphertext", models.BinaryField(default=bytes)),
                ("confirmed_at", models.DateTimeField(null=True)),
                ("last_counter", models.BigIntegerField(default=-1)),
                ("recovery_hashes", models.JSONField(default=list)),
                ("version", models.PositiveIntegerField(default=1)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="MfaChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("realm", models.CharField(choices=[("STAFF", "Staff"), ("PLATFORM", "Platform")], max_length=8)),
                ("secret_ciphertext", models.BinaryField(default=bytes)),
                ("credential_version", models.PositiveIntegerField()),
                ("staff_version", models.PositiveIntegerField(null=True)),
                ("password_digest", models.CharField(max_length=64)),
                ("replacing", models.BooleanField(default=False)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("staff", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="identity.staff")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.CheckConstraint(
                condition=models.Q(realm="STAFF", staff__isnull=False)
                | models.Q(realm="PLATFORM", staff__isnull=True),
                name="mfa_challenge_actor_realm",
            )]},
        ),
        migrations.RunPython(add_permissions, migrations.RunPython.noop),
    ]

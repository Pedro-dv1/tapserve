from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("identity", "0003_platformauditevent")]
    operations = [
        migrations.RunSQL(
            """
        CREATE FUNCTION tapserve_platform_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Platform audit is append-only' USING ERRCODE = '23514';
        END; $$;
        CREATE TRIGGER platform_audit_guard BEFORE UPDATE OR DELETE ON identity_platformauditevent
          FOR EACH ROW EXECUTE FUNCTION tapserve_platform_audit_guard();
        """,
            """
        DROP TRIGGER platform_audit_guard ON identity_platformauditevent;
        DROP FUNCTION tapserve_platform_audit_guard();
        """,
        )
    ]

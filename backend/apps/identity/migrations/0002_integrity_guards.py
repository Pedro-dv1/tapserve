from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("identity", "0001_initial")]
    operations = [
        migrations.RunSQL(
            sql="""
        CREATE FUNCTION tapserve_staff_unit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF (SELECT unit_id FROM identity_role WHERE id = NEW.role_id) IS DISTINCT FROM NEW.unit_id THEN
            RAISE EXCEPTION 'Staff role scope mismatch' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER staff_unit_guard BEFORE INSERT OR UPDATE ON identity_staff
          FOR EACH ROW EXECUTE FUNCTION tapserve_staff_unit_guard();
        CREATE FUNCTION tapserve_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'Audit is append-only' USING ERRCODE = '23514';
          END IF;
          IF NEW.staff_id IS NOT NULL AND
             (SELECT unit_id FROM identity_staff WHERE id = NEW.staff_id) IS DISTINCT FROM NEW.unit_id THEN
            RAISE EXCEPTION 'Audit actor scope mismatch' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER audit_guard BEFORE INSERT OR UPDATE OR DELETE ON identity_auditevent
          FOR EACH ROW EXECUTE FUNCTION tapserve_audit_guard();
        """,
            reverse_sql="""
        DROP TRIGGER audit_guard ON identity_auditevent;
        DROP FUNCTION tapserve_audit_guard();
        DROP TRIGGER staff_unit_guard ON identity_staff;
        DROP FUNCTION tapserve_staff_unit_guard();
        """,
        )
    ]

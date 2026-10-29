from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("orders", "0006_servicerequest_domainevent_point_orderitem_version_and_more")]
    operations = [
        migrations.RunSQL(
            """
        CREATE FUNCTION tapserve_intervention_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_TABLE_NAME='identity_auditevent' THEN
            IF NEW.device_id IS NOT NULL AND NEW.unit_id IS DISTINCT FROM
               (SELECT p.unit_id FROM access_deviceaccess d JOIN access_servicepoint p ON p.id=d.point_id WHERE d.id=NEW.device_id) THEN
              RAISE EXCEPTION 'Audit device scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_domainevent' THEN
            IF (NEW.session_id IS NOT NULL AND NEW.unit_id IS DISTINCT FROM
                (SELECT unit_id FROM orders_servicesession WHERE id=NEW.session_id)) OR
               (NEW.point_id IS NOT NULL AND NEW.unit_id IS DISTINCT FROM
                (SELECT unit_id FROM access_servicepoint WHERE id=NEW.point_id)) THEN
              RAISE EXCEPTION 'Event resource scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_servicerequest' THEN
            IF NEW.unit_id IS DISTINCT FROM (SELECT unit_id FROM access_servicepoint WHERE id=NEW.point_id) OR
               NEW.point_id IS DISTINCT FROM (SELECT point_id FROM access_deviceaccess WHERE id=NEW.device_id) OR
               (NEW.session_id IS NOT NULL AND NEW.unit_id IS DISTINCT FROM (SELECT unit_id FROM orders_servicesession WHERE id=NEW.session_id)) OR
               (NEW.assigned_to_id IS NOT NULL AND NEW.unit_id IS DISTINCT FROM (SELECT unit_id FROM identity_staff WHERE id=NEW.assigned_to_id)) THEN
              RAISE EXCEPTION 'Service request scope mismatch' USING ERRCODE='23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER audit_device_scope BEFORE INSERT ON identity_auditevent FOR EACH ROW EXECUTE FUNCTION tapserve_intervention_scope_guard();
        CREATE TRIGGER request_scope BEFORE INSERT OR UPDATE ON orders_servicerequest FOR EACH ROW EXECUTE FUNCTION tapserve_intervention_scope_guard();
        CREATE TRIGGER request_unit_immutable BEFORE UPDATE ON orders_servicerequest FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        DROP TRIGGER domain_event_scope ON orders_domainevent;
        CREATE TRIGGER domain_event_scope BEFORE INSERT OR UPDATE ON orders_domainevent FOR EACH ROW EXECUTE FUNCTION tapserve_intervention_scope_guard();
        """,
            """
        DROP TRIGGER domain_event_scope ON orders_domainevent;
        CREATE TRIGGER domain_event_scope BEFORE INSERT OR UPDATE ON orders_domainevent FOR EACH ROW EXECUTE FUNCTION tapserve_production_scope_guard();
        DROP TRIGGER request_unit_immutable ON orders_servicerequest;
        DROP TRIGGER request_scope ON orders_servicerequest;
        DROP TRIGGER audit_device_scope ON identity_auditevent;
        DROP FUNCTION tapserve_intervention_scope_guard();
        """,
        )
    ]

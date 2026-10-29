from django.db import migrations


def add_permissions(apps, schema_editor):
    permission = apps.get_model("identity", "Permission")
    role = apps.get_model("identity", "Role")
    defaults = {
        "UPDATE_PRODUCTION_STATUS": ["OWNER", "ADMIN", "MANAGER", "KITCHEN", "BAR"],
        "CLAIM_DELIVERY": ["OWNER", "ADMIN", "MANAGER", "WAITER"],
        "COMPLETE_DELIVERY": ["OWNER", "ADMIN", "MANAGER", "WAITER"],
    }
    for code, names in defaults.items():
        grant, _ = permission.objects.get_or_create(code=code)
        for template in role.objects.filter(name__in=names):
            template.suggested_permissions.add(grant)
    # Existing effective staff grants are deliberately unchanged.


class Migration(migrations.Migration):
    dependencies = [("orders", "0004_itemstatusevent_domainevent_productionassignment_and_more")]
    operations = [
        migrations.RunPython(add_permissions, migrations.RunPython.noop),
        migrations.RunSQL(
            """
        CREATE FUNCTION tapserve_production_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE scope_id uuid;
        BEGIN
          IF TG_TABLE_NAME='orders_productionassignment' THEN
            IF (SELECT unit_id FROM identity_staff WHERE id=NEW.staff_id) IS DISTINCT FROM
               (SELECT unit_id FROM catalog_productionsector WHERE id=NEW.sector_id) THEN
              RAISE EXCEPTION 'Production assignment scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_itemstatusevent' THEN
            IF TG_OP!='INSERT' THEN RAISE EXCEPTION 'Status history is append-only' USING ERRCODE='23514'; END IF;
            IF (SELECT s.unit_id FROM orders_orderitem i JOIN orders_orderbatch b ON b.id=i.batch_id JOIN orders_servicesession s ON s.id=b.session_id WHERE i.id=NEW.item_id) IS DISTINCT FROM
               (SELECT unit_id FROM identity_staff WHERE id=NEW.staff_id) THEN
              RAISE EXCEPTION 'Status history scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_domainevent' THEN
            IF NEW.unit_id IS DISTINCT FROM (SELECT unit_id FROM orders_servicesession WHERE id=NEW.session_id) THEN
              RAISE EXCEPTION 'Event scope mismatch' USING ERRCODE='23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER production_assignment_scope BEFORE INSERT OR UPDATE ON orders_productionassignment FOR EACH ROW EXECUTE FUNCTION tapserve_production_scope_guard();
        CREATE TRIGGER item_status_history BEFORE INSERT OR UPDATE OR DELETE ON orders_itemstatusevent FOR EACH ROW EXECUTE FUNCTION tapserve_production_scope_guard();
        CREATE TRIGGER domain_event_scope BEFORE INSERT OR UPDATE ON orders_domainevent FOR EACH ROW EXECUTE FUNCTION tapserve_production_scope_guard();
        CREATE TRIGGER socket_unit_immutable BEFORE UPDATE ON orders_realtimelease FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        CREATE FUNCTION tapserve_domain_notify() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          PERFORM pg_notify('tapserve_events_' || md5(TG_TABLE_SCHEMA), NEW.id::text);
          RETURN NEW;
        END; $$;
        CREATE TRIGGER domain_notify AFTER INSERT ON orders_domainevent FOR EACH ROW EXECUTE FUNCTION tapserve_domain_notify();
        """,
            """
        DROP TRIGGER domain_notify ON orders_domainevent;
        DROP FUNCTION tapserve_domain_notify();
        DROP TRIGGER socket_unit_immutable ON orders_realtimelease;
        DROP TRIGGER domain_event_scope ON orders_domainevent;
        DROP TRIGGER item_status_history ON orders_itemstatusevent;
        DROP TRIGGER production_assignment_scope ON orders_productionassignment;
        DROP FUNCTION tapserve_production_scope_guard();
        """,
        ),
    ]

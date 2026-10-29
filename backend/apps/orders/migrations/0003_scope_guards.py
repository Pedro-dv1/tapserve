from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_orderbatch_batch_exactly_one_actor"),
        ("access", "0002_deviceaccess_session"),
    ]
    operations = [
        migrations.RunSQL(
            """
        CREATE FUNCTION tapserve_order_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE scope_id uuid; v_session_id uuid;
        BEGIN
          IF TG_TABLE_NAME='orders_sessionpoint' THEN
            IF (SELECT unit_id FROM orders_servicesession WHERE id=NEW.session_id) IS DISTINCT FROM
               (SELECT unit_id FROM access_servicepoint WHERE id=NEW.point_id) THEN
              RAISE EXCEPTION 'Session point scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='access_deviceaccess' THEN
            IF NEW.session_id IS NOT NULL AND (SELECT unit_id FROM orders_servicesession WHERE id=NEW.session_id) IS DISTINCT FROM
               (SELECT unit_id FROM access_servicepoint WHERE id=NEW.point_id) THEN
              RAISE EXCEPTION 'Device scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_orderbatch' THEN
            SELECT unit_id INTO scope_id FROM orders_servicesession WHERE id=NEW.session_id;
            IF scope_id IS DISTINCT FROM (SELECT unit_id FROM orders_servicesession WHERE id=NEW.origin_session_id)
               OR (NEW.staff_id IS NOT NULL AND scope_id IS DISTINCT FROM (SELECT unit_id FROM identity_staff WHERE id=NEW.staff_id))
               OR (NEW.device_id IS NOT NULL AND scope_id IS DISTINCT FROM (SELECT p.unit_id FROM access_deviceaccess d JOIN access_servicepoint p ON p.id=d.point_id WHERE d.id=NEW.device_id)) THEN
              RAISE EXCEPTION 'Batch scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_orderitem' THEN
            SELECT b.session_id, s.unit_id INTO v_session_id, scope_id FROM orders_orderbatch b JOIN orders_servicesession s ON s.id=b.session_id WHERE b.id=NEW.batch_id;
            IF scope_id IS DISTINCT FROM (SELECT unit_id FROM catalog_product WHERE id=NEW.product_id)
               OR scope_id IS DISTINCT FROM (SELECT unit_id FROM catalog_productionsector WHERE id=NEW.sector_id)
               OR (NEW.participant_id IS NOT NULL AND v_session_id IS DISTINCT FROM (SELECT session_id FROM orders_sessionparticipant WHERE id=NEW.participant_id))
               OR (NEW.delivered_by_id IS NOT NULL AND scope_id IS DISTINCT FROM (SELECT unit_id FROM identity_staff WHERE id=NEW.delivered_by_id)) THEN
              RAISE EXCEPTION 'Order item scope mismatch' USING ERRCODE='23514';
            END IF;
          ELSIF TG_TABLE_NAME='orders_selectedoption' THEN
            SELECT s.unit_id INTO scope_id FROM orders_orderitem i JOIN orders_orderbatch b ON b.id=i.batch_id JOIN orders_servicesession s ON s.id=b.session_id WHERE i.id=NEW.item_id;
            IF scope_id IS DISTINCT FROM (SELECT p.unit_id FROM catalog_option o JOIN catalog_optiongroup g ON g.id=o.group_id JOIN catalog_product p ON p.id=g.product_id WHERE o.id=NEW.option_id) THEN
              RAISE EXCEPTION 'Selected option scope mismatch' USING ERRCODE='23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$;
        CREATE CONSTRAINT TRIGGER session_point_scope AFTER INSERT OR UPDATE ON orders_sessionpoint DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION tapserve_order_scope_guard();
        CREATE CONSTRAINT TRIGGER device_session_scope AFTER INSERT OR UPDATE ON access_deviceaccess DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION tapserve_order_scope_guard();
        CREATE CONSTRAINT TRIGGER batch_scope AFTER INSERT OR UPDATE ON orders_orderbatch DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION tapserve_order_scope_guard();
        CREATE CONSTRAINT TRIGGER order_item_scope AFTER INSERT OR UPDATE ON orders_orderitem DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION tapserve_order_scope_guard();
        CREATE CONSTRAINT TRIGGER selected_option_scope AFTER INSERT OR UPDATE ON orders_selectedoption DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION tapserve_order_scope_guard();
        CREATE TRIGGER session_unit_immutable BEFORE UPDATE ON orders_servicesession FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        CREATE TRIGGER point_unit_immutable BEFORE UPDATE ON access_servicepoint FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        CREATE TRIGGER staff_unit_immutable BEFORE UPDATE ON identity_staff FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        CREATE TRIGGER role_unit_immutable BEFORE UPDATE ON identity_role FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        """,
            """
        DROP TRIGGER role_unit_immutable ON identity_role;
        DROP TRIGGER staff_unit_immutable ON identity_staff;
        DROP TRIGGER point_unit_immutable ON access_servicepoint;
        DROP TRIGGER session_unit_immutable ON orders_servicesession;
        DROP TRIGGER selected_option_scope ON orders_selectedoption;
        DROP TRIGGER order_item_scope ON orders_orderitem;
        DROP TRIGGER batch_scope ON orders_orderbatch;
        DROP TRIGGER device_session_scope ON access_deviceaccess;
        DROP TRIGGER session_point_scope ON orders_sessionpoint;
        DROP FUNCTION tapserve_order_scope_guard();
        """,
        )
    ]

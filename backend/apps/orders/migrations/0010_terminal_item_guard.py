from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("orders", "0009_remove_orderitem_item_status_valid_and_more")]
    operations = [
        migrations.RunSQL(
            """
            CREATE FUNCTION tapserve_terminal_item_guard() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF OLD.status IN ('DELIVERED', 'CANCELLED', 'REJECTED') AND
                 (NEW.status IS DISTINCT FROM OLD.status OR NEW.snapshot IS DISTINCT FROM OLD.snapshot OR
                  NEW.quantity IS DISTINCT FROM OLD.quantity OR NEW.line_total IS DISTINCT FROM OLD.line_total OR
                  NEW.unit_price IS DISTINCT FROM OLD.unit_price) THEN
                RAISE EXCEPTION 'Terminal item is immutable' USING ERRCODE='23514';
              END IF;
              IF NEW.status='REJECTED' AND OLD.status NOT IN ('NEW', 'REJECTED') THEN
                RAISE EXCEPTION 'Only new items can be rejected' USING ERRCODE='23514';
              END IF;
              RETURN NEW;
            END; $$;
            CREATE TRIGGER terminal_item_guard BEFORE UPDATE ON orders_orderitem
              FOR EACH ROW EXECUTE FUNCTION tapserve_terminal_item_guard();
            """,
            "DROP TRIGGER terminal_item_guard ON orders_orderitem; DROP FUNCTION tapserve_terminal_item_guard();",
        )
    ]

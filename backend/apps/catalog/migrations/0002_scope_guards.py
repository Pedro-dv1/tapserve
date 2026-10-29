from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("access", "0001_initial"),
        ("identity", "0005_idempotencyrecord"),
    ]
    operations = [
        migrations.RunSQL(
            """
        CREATE FUNCTION tapserve_product_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF (SELECT m.unit_id FROM catalog_category c JOIN catalog_menu m ON m.id=c.menu_id WHERE c.id=NEW.category_id) IS DISTINCT FROM NEW.unit_id
             OR (SELECT unit_id FROM catalog_productionsector WHERE id=NEW.production_sector_id) IS DISTINCT FROM NEW.unit_id THEN
            RAISE EXCEPTION 'Product scope mismatch' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER product_scope_guard BEFORE INSERT OR UPDATE ON catalog_product
          FOR EACH ROW EXECUTE FUNCTION tapserve_product_scope_guard();
        CREATE FUNCTION tapserve_parent_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_TABLE_NAME='catalog_category' AND EXISTS (
            SELECT 1 FROM catalog_product p JOIN catalog_menu m ON m.id=NEW.menu_id
            WHERE p.category_id=NEW.id AND p.unit_id<>m.unit_id
          ) THEN
            RAISE EXCEPTION 'Category scope mismatch' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER category_scope_guard BEFORE UPDATE ON catalog_category
          FOR EACH ROW EXECUTE FUNCTION tapserve_parent_scope_guard();
        CREATE FUNCTION tapserve_unit_immutable_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.unit_id IS DISTINCT FROM NEW.unit_id THEN
            RAISE EXCEPTION 'Unit reassignment requires a governed migration' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER menu_unit_immutable BEFORE UPDATE ON catalog_menu FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        CREATE TRIGGER sector_unit_immutable BEFORE UPDATE ON catalog_productionsector FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        CREATE TRIGGER product_unit_immutable BEFORE UPDATE ON catalog_product FOR EACH ROW EXECUTE FUNCTION tapserve_unit_immutable_guard();
        """,
            """
        DROP TRIGGER product_unit_immutable ON catalog_product;
        DROP TRIGGER sector_unit_immutable ON catalog_productionsector;
        DROP TRIGGER menu_unit_immutable ON catalog_menu;
        DROP FUNCTION tapserve_unit_immutable_guard();
        DROP TRIGGER category_scope_guard ON catalog_category;
        DROP FUNCTION tapserve_parent_scope_guard();
        DROP TRIGGER product_scope_guard ON catalog_product;
        DROP FUNCTION tapserve_product_scope_guard();
        """,
        )
    ]

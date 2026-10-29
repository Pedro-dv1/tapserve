from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0007_intervention_guards")]

    operations = [
        migrations.AddField(
            model_name="orderbatch",
            name="notes",
            field=models.CharField(blank=True, default="", max_length=500),
            preserve_default=False,
        ),
    ]

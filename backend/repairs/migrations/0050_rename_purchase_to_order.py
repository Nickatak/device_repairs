"""Purchase → Order rename (2026-08-04) + the 'job' kind.

The model was always a batch-intake event, not strictly a buy: gifts,
own-stock seeds, and now customer work orders all live here. Renames only —
no data rewritten. kind='job' = customer property in for service (payload
device-shaped, total_price 0, fee rides the Exit).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0049_notetemplateentry_placeholder"),
    ]

    operations = [
        migrations.RenameModel(old_name="Purchase", new_name="Order"),
        migrations.RenameField(
            model_name="order", old_name="purchased_on", new_name="ordered_on"
        ),
        migrations.RenameField(
            model_name="device", old_name="purchase", new_name="order"
        ),
        migrations.RenameField(
            model_name="stockintake", old_name="purchase", new_name="order"
        ),
        migrations.AlterField(
            model_name="order",
            name="kind",
            field=models.CharField(
                choices=[("device", "Devices"), ("parts", "Parts"), ("job", "Jobs")],
                default="device",
                max_length=10,
            ),
        ),
    ]

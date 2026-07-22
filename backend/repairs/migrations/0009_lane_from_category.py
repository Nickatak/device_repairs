"""Data migration: create a Lane per existing category value and point each row at it.

Forward fills the new lane FK from the old category enum; reverse restores category
from the lane name so 0008 can unwind cleanly.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    Lane = apps.get_model("repairs", "Lane")
    DeviceReference = apps.get_model("repairs", "DeviceReference")

    for row in DeviceReference.objects.all():
        lane, _ = Lane.objects.get_or_create(name=row.category)
        row.lane = lane
        row.save(update_fields=["lane"])


def backwards(apps, schema_editor):
    DeviceReference = apps.get_model("repairs", "DeviceReference")

    for row in DeviceReference.objects.select_related("lane"):
        if row.lane:
            row.category = row.lane.name
            row.save(update_fields=["category"])


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0008_lane_alter_devicereference_options_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

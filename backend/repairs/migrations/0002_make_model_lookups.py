"""Promote Device.make / Device.model from CharFields to free-text lookup FKs.

Step 1 of 2: create the Make and DeviceModel tables, add temporary FK columns,
and backfill them from the existing string values. Step 2 (0003) drops the old
CharFields and renames the FK columns into place. Split so the backfill runs while
both the old strings and the new FKs coexist — no data loss.
"""

import django.db.models.deletion
from django.db import migrations, models


def populate_lookups(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    Make = apps.get_model("repairs", "Make")
    DeviceModel = apps.get_model("repairs", "DeviceModel")
    for device in Device.objects.all():
        if device.make:
            device.make_ref = Make.objects.get_or_create(name=device.make)[0]
        if device.model:
            device.model_ref = DeviceModel.objects.get_or_create(name=device.model)[0]
        device.save(update_fields=["make_ref", "model_ref"])


def reverse_lookups(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    for device in Device.objects.all():
        device.make = device.make_ref.name if device.make_ref_id else ""
        device.model = device.model_ref.name if device.model_ref_id else ""
        device.save(update_fields=["make", "model"])


class Migration(migrations.Migration):
    dependencies = [("repairs", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Make",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DeviceModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
            ],
            options={"verbose_name": "model", "verbose_name_plural": "models", "ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="device",
            name="make_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="devices",
                to="repairs.make",
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="model_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="devices",
                to="repairs.devicemodel",
            ),
        ),
        migrations.RunPython(populate_lookups, reverse_lookups),
    ]

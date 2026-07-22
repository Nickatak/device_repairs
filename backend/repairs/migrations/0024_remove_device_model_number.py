"""Retire Device.model_number — label numbers live on the catalog row now.

Hand-written for the data step: each device's model_number is promoted to its
reference's comma-separated model_numbers if absent there (the catalog's
"blank until seen on a real unit" flow); devices without a reference keep the
value in notes so nothing is lost.
"""

from django.db import migrations


def promote_to_catalog(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    for device in Device.objects.exclude(model_number="").select_related("reference"):
        value = device.model_number.strip()
        ref = device.reference
        if ref is not None:
            existing = [p.strip() for p in ref.model_numbers.split(",") if p.strip()]
            if value not in existing:
                ref.model_numbers = ", ".join(existing + [value])
                ref.save()
        else:
            device.notes = f"[label model #: {value}]\n{device.notes}".strip()
            device.save()


class Migration(migrations.Migration):
    # Data writes + ALTER on repairs_device can't share a transaction (Postgres
    # pending-trigger rule); the data step is re-runnable.
    atomic = False

    dependencies = [
        ("repairs", "0023_purchase"),
    ]

    operations = [
        migrations.RunPython(promote_to_catalog, migrations.RunPython.noop),
        migrations.RemoveField(model_name="device", name="model_number"),
    ]

"""Collapse the lifecycle to five states + add Device.to_who.

Hand-written for the data step: old statuses fold in BEFORE the choices
narrow — diagnosed → acquired ('diagnosed isn't actually a thing'); listed →
fixed; the terminal five (sold/parted/scrapped/gifted/lost) → exited with the
old value preserved as an '[exit: …]' note marker so the reason survives.
"""

from django.db import migrations, models

FOLD = {
    "diagnosed": ("acquired", False),
    "listed": ("fixed", False),
    "sold": ("exited", True),
    "parted": ("exited", True),
    "scrapped": ("exited", True),
    "gifted": ("exited", True),
    "lost": ("exited", True),
}


def fold_statuses(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    for device in Device.objects.filter(status__in=FOLD):
        new_status, mark = FOLD[device.status]
        if mark:
            device.notes = f"[exit: {device.status}]\n{device.notes}".strip()
        device.status = new_status
        device.save()


class Migration(migrations.Migration):
    # Data writes + ALTER on repairs_device can't share a transaction (Postgres
    # pending-trigger rule); the data step is re-runnable.
    atomic = False

    dependencies = [
        ("repairs", "0028_device_label_device_ledger_ref"),
    ]

    operations = [
        migrations.RunPython(fold_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="device",
            name="status",
            field=models.CharField(
                choices=[
                    ("shipped", "Shipped (inbound)"),
                    ("acquired", "Acquired"),
                    ("in_repair", "In repair"),
                    ("fixed", "Fixed"),
                    ("exited", "Exited"),
                ],
                default="acquired",
                help_text="Lifecycle position, manually set — mirrors the tracking ledger.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="to_who",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Who the unit went to on exit — buyer, friend. Shares the counterparty "
                    "pool with Purchase.from_who. Meaningful only when status is exited."
                ),
                max_length=120,
            ),
        ),
    ]

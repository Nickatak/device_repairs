"""Move status to Device (ledger lifecycle) and remove Repair.Status.

Order matters: add the device fields, map each device's latest-repair status onto
them, then drop the repair column. The old enum conflated bench-state and
disposition; the mapping sends each value to its ledger-lifecycle home. `wont_fix` /
`cant_fix` have no lifecycle slot (ledger practice: those units sit at `diagnosed`
with notes) — the old value is preserved as a note marker so nothing is lost.
"""

from django.db import migrations, models

# old Repair.Status value -> (Device.Status value, blocked_reason, note marker)
STATUS_MAP = {
    "shipping_to_me": ("shipped", "", ""),
    "diagnosing": ("diagnosed", "", ""),
    "repairing": ("in_repair", "", ""),
    "waiting_blocked": ("in_repair", "migrated from 'Waiting / blocked' — re-enter the real reason", ""),
    "wont_fix": ("diagnosed", "", "[status migration] was 'Won't fix (economic)'"),
    "cant_fix": ("diagnosed", "", "[status migration] was 'Can't fix (skill out of reach)'"),
    "fixed": ("fixed", "", ""),
    "shipping_to_buyer": ("sold", "", ""),
    "parted_out": ("parted", "", ""),
    "garbage": ("scrapped", "", ""),
}


def forwards(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")

    for device in Device.objects.prefetch_related("repairs"):
        latest = device.repairs.order_by("-created_at").first()
        if latest is None:
            continue  # keeps the 'acquired' default
        status, blocked, marker = STATUS_MAP[latest.status]
        device.status = status
        device.blocked_reason = blocked
        if marker:
            device.notes = f"{device.notes}\n{marker}".strip()
        device.save(update_fields=["status", "blocked_reason", "notes"])


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0012_simplify_measurement"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="status",
            field=models.CharField(
                choices=[
                    ("lead", "Lead"),
                    ("shipped", "Shipped (inbound)"),
                    ("acquired", "Acquired"),
                    ("diagnosed", "Diagnosed"),
                    ("in_repair", "In repair"),
                    ("fixed", "Fixed"),
                    ("listed", "Listed"),
                    ("sold", "Sold"),
                    ("parted", "Parted out"),
                    ("scrapped", "Scrapped"),
                    ("gifted", "Gifted"),
                    ("lost", "Lost"),
                ],
                default="acquired",
                help_text="Lifecycle position, manually set — mirrors the tracking ledger.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="blocked_reason",
            field=models.CharField(
                blank=True,
                help_text="Why the unit is stuck ('waiting on hall modules'). Blank = not blocked.",
                max_length=200,
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="repair",
            name="status",
        ),
    ]

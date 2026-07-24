# in_repair/fixed split into the two bench families (Nick, 2026-07-24):
# Disassembled: {Diagnosing, Parts, Solder} — physically open on the desk,
# sub-state = what the unit is waiting for — and Re-assembled: {Untested,
# Tested}. Data map here uses the safe generic defaults (in_repair →
# disassembled_diagnosing, fixed → reassembled_tested); the per-unit truth
# (0024-2 → untested, 0024-1 → parts, 0004-4 → solder) is applied via the API
# after deploy so both instances take it through the same write path.

from django.db import migrations, models

FORWARD = {"in_repair": "disassembled_diagnosing", "fixed": "reassembled_tested"}
# Reverse collapses each family back to the old single state.
REVERSE = {
    "disassembled_diagnosing": "in_repair",
    "disassembled_parts": "in_repair",
    "disassembled_solder": "in_repair",
    "reassembled_untested": "in_repair",
    "reassembled_tested": "fixed",
}


def remap(apps, mapping):
    Device = apps.get_model("repairs", "Device")
    for old, new in mapping.items():
        Device.objects.filter(status=old).update(status=new)


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0039_media_timestamps"),
    ]

    operations = [
        migrations.AlterField(
            model_name="device",
            name="status",
            field=models.CharField(
                choices=[
                    ("shipped", "Shipped (inbound)"),
                    ("acquired", "Acquired"),
                    ("disassembled_diagnosing", "Disassembled: Diagnosing"),
                    ("disassembled_parts", "Disassembled: Parts"),
                    ("disassembled_solder", "Disassembled: Solder"),
                    ("reassembled_untested", "Re-assembled: Untested"),
                    ("reassembled_tested", "Re-assembled: Tested"),
                    ("exited", "Exited"),
                ],
                default="acquired",
                help_text="Lifecycle position, manually set — mirrors the tracking ledger.",
                max_length=40,
            ),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: remap(apps, FORWARD),
            lambda apps, schema_editor: remap(apps, REVERSE),
        ),
    ]

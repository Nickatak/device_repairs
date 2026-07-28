# "Re-assembled: Tested" → "Awaiting exit" (2026-07-28): the terminal
# pre-exit state is a PIPELINE position, not a quality claim — a unit
# waiting on a scrap exit sits here too. Value renamed with the label so
# the API string doesn't lie.

from django.db import migrations, models


def rename_forward(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    Device.objects.filter(status="reassembled_tested").update(status="awaiting_exit")


def rename_back(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    Device.objects.filter(status="awaiting_exit").update(status="reassembled_tested")


class Migration(migrations.Migration):

    dependencies = [
        ("repairs", "0047_fold_phase_notes_into_step_notes"),
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
                    ("awaiting_exit", "Awaiting exit"),
                    ("exited", "Exited"),
                ],
                default="acquired",
                help_text="Lifecycle position, manually set — mirrors the tracking ledger.",
                max_length=40,
            ),
        ),
        migrations.RunPython(rename_forward, rename_back),
    ]

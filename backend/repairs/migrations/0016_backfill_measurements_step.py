"""Backfill the standing "Measurements" bucket step onto existing repairs.

Every repair carries one from creation now (Repair.save); this brings the
pre-existing rows up to the same invariant. Skips repairs that already have a
top-level step titled "Measurements".
"""

from django.db import migrations


def forwards(apps, schema_editor):
    Repair = apps.get_model("repairs", "Repair")
    Step = apps.get_model("repairs", "Step")

    for repair in Repair.objects.all():
        if not repair.steps.filter(parent__isnull=True, title="Measurements").exists():
            Step.objects.create(repair=repair, position=0, title="Measurements")


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0015_remove_step_type"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

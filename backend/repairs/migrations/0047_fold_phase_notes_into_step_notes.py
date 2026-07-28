# The per-phase deviation text layer retires (2026-07-28 cleanup pass):
# per-phase step Notes replaced it. Every non-blank {phase}_note becomes a
# step Note on that phase (title blank, text verbatim, appended after the
# repair's existing positions), then the seven columns drop. No text is lost.

from django.db import migrations
from django.db.models import Max

PHASE_KEYS = ["intake", "teardown", "diagnostics", "repair", "wash", "reassemble", "verify"]


def fold_into_step_notes(apps, schema_editor):
    Repair = apps.get_model("repairs", "Repair")
    Note = apps.get_model("repairs", "Note")
    for repair in Repair.objects.all():
        next_pos = (repair.notes.aggregate(m=Max("position"))["m"] or 0) + 1
        for key in PHASE_KEYS:
            text = getattr(repair, f"{key}_note")
            if text and text.strip():
                Note.objects.create(
                    repair=repair, phase=key, position=next_pos, title="", text=text
                )
                next_pos += 1


class Migration(migrations.Migration):

    dependencies = [
        ("repairs", "0046_note_timestamps"),
    ]

    operations = [
        migrations.RunPython(fold_into_step_notes, migrations.RunPython.noop),
        *[
            migrations.RemoveField(model_name="repair", name=f"{key}_note")
            for key in PHASE_KEYS
        ],
    ]

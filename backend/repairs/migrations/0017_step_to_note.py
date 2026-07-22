"""Vocab rename: Step → Note (Nick, 2026-07-21), plus Repair.completed_at.

"Note" was already taken by free-text commentary fields on the affected models, so
those rename to `comment` first (measurement.note, repair.notes, step.notes) — then
the model renames, then the child FKs. Media's check constraint is dropped and
re-added around its FK rename so the state never references a missing field.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0016_backfill_measurements_step"),
    ]

    operations = [
        # Free the name "note"/"notes" on every model that gains a Note FK.
        migrations.RenameField("measurement", "note", "comment"),
        migrations.RenameField("part", "note", "comment"),
        migrations.RenameField("repair", "notes", "comment"),
        migrations.RenameField("step", "notes", "comment"),
        # The model itself.
        migrations.RenameModel("Step", "Note"),
        # Child FKs point at "note" now.
        migrations.RenameField("measurement", "step", "note"),
        migrations.RenameField("part", "step", "note"),
        migrations.RemoveConstraint("media", "media_attaches_to_exactly_one_parent"),
        migrations.RenameField("media", "step", "note"),
        migrations.AddConstraint(
            "media",
            models.CheckConstraint(
                condition=(
                    models.Q(repair__isnull=False, note__isnull=True)
                    | models.Q(repair__isnull=True, note__isnull=False)
                ),
                name="media_attaches_to_exactly_one_parent",
            ),
        ),
        # Manual completion mark, after Verify.
        migrations.AddField(
            model_name="repair",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Manual completion mark, after Verify. Unchecked phases on a "
                    "completed repair demonstrably did NOT happen."
                ),
                null=True,
            ),
        ),
        # State-only alignment: renamed related_names / updated help_texts.
        migrations.AlterField(
            model_name="note",
            name="repair",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notes",
                to="repairs.repair",
            ),
        ),
        migrations.AlterField(
            model_name="note",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subnotes",
                to="repairs.note",
            ),
        ),
    ]

# Notes go per-phase + the note-template layer (2026-07-28).
#
# Every Note now belongs to a repair-substep. Backfill: the standing
# position-0 "Measurements" buckets move to Diagnostics (their natural home);
# every other pre-existing note lands on Repair as the safe default — Nick's
# cleanup pass re-files any that belong elsewhere. Sub-notes then sync to
# their parent's phase.

from django.db import migrations, models
import django.db.models.deletion

PHASE_CHOICES = [
    ("intake", "Intake"),
    ("teardown", "Teardown"),
    ("diagnostics", "Diagnostics"),
    ("repair", "Repair"),
    ("wash", "Wash"),
    ("reassemble", "Re-assemble"),
    ("verify", "Verify"),
]


def backfill_phases(apps, schema_editor):
    Note = apps.get_model("repairs", "Note")
    Note.objects.filter(parent__isnull=True, position=0, title="Measurements").update(
        phase="diagnostics"
    )
    for sub in Note.objects.filter(parent__isnull=False).select_related("parent"):
        if sub.phase != sub.parent.phase:
            Note.objects.filter(pk=sub.pk).update(phase=sub.parent.phase)


class Migration(migrations.Migration):

    dependencies = [
        ("repairs", "0044_repair_diagnostics_done_at_repair_diagnostics_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="note",
            name="phase",
            field=models.CharField(
                choices=PHASE_CHOICES,
                default="repair",
                help_text="The repair-substep this note documents. Sub-notes follow their parent.",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="NoteTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phase", models.CharField(choices=PHASE_CHOICES, max_length=20)),
                (
                    "name",
                    models.CharField(
                        help_text="Dropdown label — 'Hall Mod', 'Voltage readings'.", max_length=120
                    ),
                ),
                (
                    "reference",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="note_templates",
                        to="repairs.devicereference",
                    ),
                ),
            ],
            options={"ordering": ["reference", "phase"]},
        ),
        migrations.AddConstraint(
            model_name="notetemplate",
            constraint=models.UniqueConstraint(
                fields=("reference", "phase"), name="one_template_per_reference_per_phase"
            ),
        ),
        migrations.CreateModel(
            name="NoteTemplateEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveIntegerField(default=0)),
                ("title", models.CharField(blank=True, help_text="Prefilled note title.", max_length=255)),
                ("text", models.TextField(blank=True, help_text="Prefilled note body, editable in the modal.")),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="repairs.notetemplate",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
                "verbose_name_plural": "note template entries",
            },
        ),
        migrations.CreateModel(
            name="NoteTemplateMeasurement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveIntegerField(default=0)),
                ("what", models.CharField(help_text="Prefilled measurement name — '1.1V rail'.", max_length=200)),
                (
                    "expected",
                    models.CharField(
                        blank=True,
                        help_text="Expected value, shown as placeholder — never auto-filled.",
                        max_length=120,
                    ),
                ),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="measurements",
                        to="repairs.notetemplateentry",
                    ),
                ),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.RunPython(backfill_phases, migrations.RunPython.noop),
    ]

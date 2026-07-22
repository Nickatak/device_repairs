"""Simplify Measurement to free text (what/value/note); drop the lookup tables.

Table had zero rows at migration time (verified 2026-07-21), so drop-and-recreate —
no data conversion path needed.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0011_repair_reassemble_done_at_repair_reassemble_note_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="Measurement"),
        migrations.DeleteModel(name="MeasurementWhat"),
        migrations.DeleteModel(name="Unit"),
        migrations.CreateModel(
            name="Measurement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "what",
                    models.CharField(
                        help_text="What was measured — '5V rail', 'C701 ESR', 'DC jack'.",
                        max_length=200,
                    ),
                ),
                (
                    "value",
                    models.CharField(
                        blank=True,
                        help_text="What it read — '4.98 V', '120 mΩ', 'no reading — pad lifted'.",
                        max_length=120,
                    ),
                ),
                (
                    "note",
                    models.TextField(
                        blank=True, help_text="The 'why', or a provisional conclusion."
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="measurements",
                        to="repairs.step",
                    ),
                ),
            ],
        ),
    ]

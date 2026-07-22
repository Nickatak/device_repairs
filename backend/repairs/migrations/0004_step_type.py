"""Step gets a Type; `observation` becomes the primary `text`; `action` is dropped.

A typed step (test / observation / repair / notation) is self-contained as {type, text},
so the old short `action` title is redundant. RenameField preserves the text column.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("repairs", "0003_finalize_make_model")]

    operations = [
        migrations.RenameField(model_name="step", old_name="observation", new_name="text"),
        migrations.RemoveField(model_name="step", name="action"),
        migrations.AddField(
            model_name="step",
            name="type",
            field=models.CharField(
                choices=[
                    ("test", "Test"),
                    ("observation", "Observation"),
                    ("repair", "Repair"),
                    ("notation", "Notation"),
                ],
                default="observation",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="step",
            name="text",
            field=models.TextField(
                blank=True,
                help_text="The step's content — what was tested / observed / repaired / noted.",
            ),
        ),
    ]

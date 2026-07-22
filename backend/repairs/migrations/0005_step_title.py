"""Add a short `title` heading to Step (sits above the `text` body)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("repairs", "0004_step_type")]

    operations = [
        migrations.AddField(
            model_name="step",
            name="title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Short heading for the step.",
                max_length=255,
            ),
            preserve_default=False,
        ),
    ]

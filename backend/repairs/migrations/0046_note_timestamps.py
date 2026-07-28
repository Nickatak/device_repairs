# Note gains created_at/updated_at (2026-07-28) — the phase accordion shows
# "most recent note + when". Existing rows stamp at migration time; real
# recency accrues from here.

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("repairs", "0045_note_phase_and_templates"),
    ]

    operations = [
        migrations.AddField(
            model_name="note",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="note",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]

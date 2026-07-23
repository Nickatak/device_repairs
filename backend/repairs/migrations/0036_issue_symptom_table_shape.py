"""Issue reshape: verdict chips → symptom-decomposition table.

title becomes fault (the symptom as a listing shows it) and the row gains
category + cause — 'Power | No power | PSU/5V MOSFET | buy'. Existing
parser-imported rows are superseded by the hand-converted issues_seed.json
(seed_issues wipes-and-reseeds them; see that command).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0035_issue"),
    ]

    operations = [
        migrations.RenameField(model_name="issue", old_name="title", new_name="fault"),
        migrations.AlterField(
            model_name="issue",
            name="fault",
            field=models.CharField(
                help_text="The symptom as a listing shows it — 'No power', 'RROD', 'Stick drift'.",
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="category",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Subsystem grouping — Power, Display, Board, Input, Intake…",
                max_length=40,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="issue",
            name="cause",
            field=models.CharField(
                blank=True,
                default="",
                help_text="What the symptom decodes to — 'PSU / 5V MOSFET', 'APU BGA'.",
                max_length=200,
            ),
            preserve_default=False,
        ),
    ]

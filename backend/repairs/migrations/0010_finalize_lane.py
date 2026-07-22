"""Finalize the category→lane move: drop the enum column, make lane required.

Safe because 0009 filled lane for every existing row.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0009_lane_from_category"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="devicereference",
            name="category",
        ),
        migrations.AlterField(
            model_name="devicereference",
            name="lane",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="references",
                to="repairs.lane",
            ),
        ),
    ]

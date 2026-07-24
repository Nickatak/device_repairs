# Media grows its two timestamps: taken_at (EXIF shutter moment, extracted at
# upload) and created_at (row stamp). The table is empty on both instances at
# migration time (verified 2026-07-24), so the one-off default never touches a
# real row.

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0038_part_created_at_revision_device_revision_stockitem_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="media",
            name="taken_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    "Shutter moment from EXIF DateTimeOriginal, stored UTC "
                    "(bench-local assumed when the camera wrote no offset). "
                    "Null = no EXIF timestamp."
                ),
            ),
        ),
        migrations.AddField(
            model_name="media",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]

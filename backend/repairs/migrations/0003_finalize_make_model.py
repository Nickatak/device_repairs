"""Step 2 of 2: drop the old string columns and rename the FK columns into place.

After this, Device.make is a FK to Make and Device.model a FK to DeviceModel,
matching models.py. The backfill in 0002 has already moved the data across.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("repairs", "0002_make_model_lookups")]

    operations = [
        migrations.RemoveField(model_name="device", name="make"),
        migrations.RemoveField(model_name="device", name="model"),
        migrations.RenameField(model_name="device", old_name="make_ref", new_name="make"),
        migrations.RenameField(model_name="device", old_name="model_ref", new_name="model"),
    ]

"""Retire Make/DeviceModel: the DeviceReference catalog is device identity now.

Hand-written (RunPython + removals must be ordered; autodetector can't know the
data step). Before dropping the fields, each device's (make, model) pair is
resolved to a catalog row by exact (brand, name) match, with an alias table for
known name drift. Unmatched devices keep reference NULL and get their old
identity text prepended to notes so nothing is lost — re-point them by hand via
the device form's reference picker.
"""

from django.db import migrations

# (make, model) pairs whose names drifted from their catalog row's (brand, name).
ALIASES = {
    ("Ducky", "One 2"): ("Ducky", "One 2 RGB TKL"),
}


def link_references(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    DeviceReference = apps.get_model("repairs", "DeviceReference")
    for device in Device.objects.select_related("make", "model").filter(
        reference__isnull=True
    ):
        make = device.make.name if device.make else ""
        model = device.model.name if device.model else ""
        if not make and not model:
            continue
        brand, name = ALIASES.get((make, model), (make, model))
        ref = DeviceReference.objects.filter(brand=brand, name=name).first()
        if ref:
            device.reference = ref
        else:
            was = f"[pre-catalog identity: {make} {model}]".replace("  ", " ")
            device.notes = f"{was}\n{device.notes}".strip()
        device.save()


class Migration(migrations.Migration):
    # Postgres can't ALTER a table with pending trigger events from the data step
    # in the same transaction; the RunPython is safely re-runnable (filters on
    # reference__isnull=True), so non-atomic is fine.
    atomic = False

    dependencies = [
        ("repairs", "0018_alter_note_comment_alter_note_position_and_more"),
    ]

    operations = [
        migrations.RunPython(link_references, migrations.RunPython.noop),
        migrations.RemoveField(model_name="device", name="make"),
        migrations.RemoveField(model_name="device", name="model"),
        migrations.DeleteModel(name="Make"),
        migrations.DeleteModel(name="DeviceModel"),
    ]

# Device.notes blob → DeviceNote chunks (2026-07-27).
#
# The blob field re-edited in place; unit facts actually accrete as dated
# entries (same shape as the repair Note). Each device's non-blank blob
# becomes chunk #0 verbatim, then the field is dropped. Media gains the
# device_note parent (third XOR arm) so intake photos can ride the device
# before any repair exists.

from django.db import migrations, models
import django.db.models.deletion


def blobs_to_chunks(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    DeviceNote = apps.get_model("repairs", "DeviceNote")
    DeviceNote.objects.bulk_create(
        DeviceNote(device_id=device.pk, position=0, text=device.notes)
        for device in Device.objects.exclude(notes="")
    )


def chunks_to_blobs(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    DeviceNote = apps.get_model("repairs", "DeviceNote")
    for note in DeviceNote.objects.order_by("device_id", "position", "id"):
        device = Device.objects.get(pk=note.device_id)
        chunk = f"{note.title}\n{note.text}" if note.title else note.text
        device.notes = f"{device.notes}\n\n{chunk}" if device.notes else chunk
        device.save(update_fields=["notes"])


class Migration(migrations.Migration):

    dependencies = [
        ("repairs", "0040_status_bench_split"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "position",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Ordering on the device page; ties resolve by id (creation order).",
                    ),
                ),
                ("title", models.CharField(blank=True, help_text="Short heading for the chunk.", max_length=255)),
                ("text", models.TextField(blank=True, help_text="The fact — unit-grain, not bench-step-grain.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="device_notes",
                        to="repairs.device",
                    ),
                ),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.AddField(
            model_name="media",
            name="device_note",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="media",
                to="repairs.devicenote",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="media",
            name="media_attaches_to_exactly_one_parent",
        ),
        migrations.AddConstraint(
            model_name="media",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(repair__isnull=False, note__isnull=True, device_note__isnull=True)
                    | models.Q(repair__isnull=True, note__isnull=False, device_note__isnull=True)
                    | models.Q(repair__isnull=True, note__isnull=True, device_note__isnull=False)
                ),
                name="media_attaches_to_exactly_one_parent",
            ),
        ),
        migrations.RunPython(blobs_to_chunks, chunks_to_blobs),
        migrations.RemoveField(
            model_name="device",
            name="notes",
        ),
    ]

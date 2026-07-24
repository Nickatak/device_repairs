"""Media upload behavior — EXIF taken_at extraction, the GPS strip, parent rules."""

import io
from datetime import datetime, timezone

import piexif
from django.test import TestCase
from PIL import ExifTags, Image

from repairs.models import Device, Media, Note, Repair


def make_jpeg(exif_dict=None):
    """A tiny in-memory JPEG, optionally with a piexif-built EXIF segment."""
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format="JPEG")
    data = buf.getvalue()
    if exif_dict is not None:
        out = io.BytesIO()
        piexif.insert(piexif.dump(exif_dict), data, out)
        data = out.getvalue()
    return data


GPS_IFD = {
    piexif.GPSIFD.GPSLatitudeRef: b"N",
    piexif.GPSIFD.GPSLatitude: ((34, 1), (6, 1), (0, 1)),
    piexif.GPSIFD.GPSLongitudeRef: b"W",
    piexif.GPSIFD.GPSLongitude: ((117, 1), (48, 1), (0, 1)),
}


class MediaUploadTests(TestCase):
    def setUp(self):
        self.repair = Repair.objects.create(device=Device.objects.create())
        self.note = self.repair.notes.get(position=0)

    def upload(self, jpeg_bytes, name="bench.jpg", **extra):
        payload = {"image": io.BytesIO(jpeg_bytes), **extra}
        payload["image"].name = name
        return self.client.post("/api/v1/media/", payload)

    def stored_exif(self, media_id):
        with Media.objects.get(pk=media_id).image.open("rb") as f:
            return piexif.load(f.read())

    def test_taken_at_from_datetimeoriginal_with_offset(self):
        exif = {"Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2026:07:20 14:30:00",
            0x9011: b"-07:00",  # OffsetTimeOriginal (piexif 1.1.3 has no constant)
        }}
        res = self.upload(make_jpeg(exif), note=self.note.pk)
        self.assertEqual(res.status_code, 201, res.content)
        media = Media.objects.get(pk=res.json()["id"])
        self.assertEqual(media.taken_at, datetime(2026, 7, 20, 21, 30, tzinfo=timezone.utc))

    def test_taken_at_assumes_bench_tz_without_offset(self):
        # July in America/Los_Angeles is UTC-7 (DST) — 14:30 bench = 21:30 UTC.
        exif = {"Exif": {piexif.ExifIFD.DateTimeOriginal: b"2026:07:20 14:30:00"}}
        res = self.upload(make_jpeg(exif), note=self.note.pk)
        media = Media.objects.get(pk=res.json()["id"])
        self.assertEqual(media.taken_at, datetime(2026, 7, 20, 21, 30, tzinfo=timezone.utc))

    def test_no_exif_means_null_taken_at_and_created_at_stamps(self):
        res = self.upload(make_jpeg(), note=self.note.pk)
        media = Media.objects.get(pk=res.json()["id"])
        self.assertIsNone(media.taken_at)
        self.assertIsNotNone(media.created_at)

    def test_gps_stripped_datetime_and_device_tags_kept(self):
        exif = {
            "0th": {piexif.ImageIFD.Make: b"TestPhone Corp", piexif.ImageIFD.Model: b"TP-1"},
            "Exif": {piexif.ExifIFD.DateTimeOriginal: b"2026:07:20 14:30:00"},
            "GPS": GPS_IFD,
        }
        res = self.upload(make_jpeg(exif), note=self.note.pk)
        stored = self.stored_exif(res.json()["id"])
        self.assertEqual(stored["GPS"], {})
        self.assertEqual(stored["0th"][piexif.ImageIFD.Make], b"TestPhone Corp")
        self.assertEqual(
            stored["Exif"][piexif.ExifIFD.DateTimeOriginal], b"2026:07:20 14:30:00"
        )

    def test_gps_strip_does_not_recompress_pixels(self):
        # Lossless segment swap: pixel data identical before and after the strip.
        original = make_jpeg({"GPS": GPS_IFD})
        res = self.upload(original, note=self.note.pk)
        with Media.objects.get(pk=res.json()["id"]).image.open("rb") as f:
            stored = f.read()
        self.assertEqual(
            list(Image.open(io.BytesIO(original)).getdata()),
            list(Image.open(io.BytesIO(stored)).getdata()),
        )

    def test_attaches_to_repair_directly(self):
        res = self.upload(make_jpeg(), repair=self.repair.pk)
        self.assertEqual(res.status_code, 201, res.content)

    def test_rejects_both_parents_and_neither(self):
        self.assertEqual(
            self.upload(make_jpeg(), note=self.note.pk, repair=self.repair.pk).status_code, 400
        )
        self.assertEqual(self.upload(make_jpeg()).status_code, 400)

    def test_completed_repair_is_frozen(self):
        self.repair.completed_at = datetime(2026, 7, 24, tzinfo=timezone.utc)
        self.repair.save()
        self.assertEqual(self.upload(make_jpeg(), note=self.note.pk).status_code, 400)

    def test_patch_caption_but_not_image(self):
        res = self.upload(make_jpeg(), note=self.note.pk)
        url = f"/api/v1/media/{res.json()['id']}/"
        ok = self.client.patch(url, {"caption": "lifted pad, pre-bodge"}, content_type="application/json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["caption"], "lifted pad, pre-bodge")

    def test_media_nested_in_device_payload(self):
        res = self.upload(make_jpeg(), note=self.note.pk, caption="bad trace")
        device_payload = self.client.get(f"/api/v1/inventory/{self.repair.device_id}/").json()
        note_payload = device_payload["repairs"][0]["notes"][0]
        self.assertEqual(note_payload["media"][0]["caption"], "bad trace")
        self.assertTrue(note_payload["media"][0]["image"].startswith("/media/"))

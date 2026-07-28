"""Device notes — unit-fact chunks replacing the Device.notes blob (2026-07-27).

Chunks accrete like repair notes (add, edit, no delete) and carry photos, so
intake/listing shots have a home before any repair exists. The repair-log
freeze never applies here — device facts stay writable for the unit's life.
"""

import io
from datetime import datetime, timezone

from django.test import TestCase

from repairs.models import Device, DeviceNote, Media, Repair

from .test_media import make_jpeg


class DeviceNoteApiTests(TestCase):
    def setUp(self):
        self.device = Device.objects.create()

    def post_chunk(self, **payload):
        return self.client.post(
            "/api/v1/device-notes/",
            {"device": self.device.pk, **payload},
            content_type="application/json",
        )

    def test_create_chunk_and_read_back_in_detail_payload(self):
        res = self.post_chunk(title="Intake", text="Fault: no charge", position=0)
        self.assertEqual(res.status_code, 201, res.content)
        payload = self.client.get(f"/api/v1/inventory/{self.device.pk}/").json()
        self.assertEqual(len(payload["device_notes"]), 1)
        chunk = payload["device_notes"][0]
        self.assertEqual(chunk["title"], "Intake")
        self.assertEqual(chunk["text"], "Fault: no charge")
        self.assertIsNotNone(chunk["created_at"])

    def test_chunks_order_by_position_then_id(self):
        self.post_chunk(text="second", position=1)
        self.post_chunk(text="first", position=0)
        self.post_chunk(text="third", position=1)  # same position → id breaks the tie
        payload = self.client.get(f"/api/v1/inventory/{self.device.pk}/").json()
        self.assertEqual(
            [c["text"] for c in payload["device_notes"]], ["first", "second", "third"]
        )

    def test_patch_chunk(self):
        chunk_id = self.post_chunk(text="rev TBD").json()["id"]
        res = self.client.patch(
            f"/api/v1/device-notes/{chunk_id}/",
            {"text": "rev read: JDM-055"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(DeviceNote.objects.get(pk=chunk_id).text, "rev read: JDM-055")

    def test_no_delete_route(self):
        chunk_id = self.post_chunk(text="permanent").json()["id"]
        res = self.client.delete(f"/api/v1/device-notes/{chunk_id}/")
        self.assertEqual(res.status_code, 405)

    def test_device_create_notes_spawns_first_chunk(self):
        res = self.client.post(
            "/api/v1/inventory/",
            {"status": "acquired", "notes": "Fault: drift, left stick"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        device = Device.objects.latest("pk")
        chunk = device.device_notes.get()
        self.assertEqual(chunk.position, 0)
        self.assertEqual(chunk.text, "Fault: drift, left stick")

    def test_device_patch_with_notes_is_a_loud_400(self):
        # Old clients sending the dead blob field must fail, not silently drop.
        res = self.client.patch(
            f"/api/v1/inventory/{self.device.pk}/",
            {"notes": "edited blob"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.device.device_notes.count(), 0)

    def test_list_payload_flattens_chunks_for_search(self):
        self.post_chunk(title="Intake", text="Fault: dead", position=0)
        self.post_chunk(text="smoker lot", position=1)
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertEqual(row["notes"], "Intake\nFault: dead\n\nsmoker lot")


class DeviceNoteMediaTests(TestCase):
    def setUp(self):
        self.device = Device.objects.create()
        self.chunk = DeviceNote.objects.create(device=self.device, text="intake shots")

    def upload(self, **extra):
        image = io.BytesIO(make_jpeg())
        image.name = "intake.jpg"
        return self.client.post("/api/v1/media/", {"image": image, **extra})

    def test_photo_attaches_to_device_note_and_nests_in_payload(self):
        res = self.upload(device_note=self.chunk.pk, caption="shell scuff, as bought")
        self.assertEqual(res.status_code, 201, res.content)
        payload = self.client.get(f"/api/v1/inventory/{self.device.pk}/").json()
        media = payload["device_notes"][0]["media"]
        self.assertEqual(media[0]["caption"], "shell scuff, as bought")
        self.assertTrue(media[0]["image"].startswith("/media/"))

    def test_rejects_device_note_plus_repair_parents(self):
        repair = Repair.objects.create(device=self.device)
        res = self.upload(device_note=self.chunk.pk, repair=repair.pk)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Media.objects.count(), 0)

    def test_device_note_media_unaffected_by_completed_repair(self):
        # The freeze guards the repair log; unit-grain photos stay writable.
        Repair.objects.create(
            device=self.device, completed_at=datetime(2026, 7, 26, tzinfo=timezone.utc)
        )
        res = self.upload(device_note=self.chunk.pk)
        self.assertEqual(res.status_code, 201, res.content)

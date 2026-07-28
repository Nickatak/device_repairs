"""Device.touched_at — one stamp for 'anything in this unit's tree changed'.

Every write path bumps it: device fields, device notes, repairs, repair notes,
measurements, media (all three parents), exits, and the arrival status flip
(which bypasses save()). Writes on one device must never bump another.
"""

import io
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase

from repairs.models import Device, DeviceNote, Purchase, Repair

from .test_media import make_jpeg

LONG_AGO = datetime(2020, 1, 1, tzinfo=dt_timezone.utc)


class TouchedAtTests(TestCase):
    def setUp(self):
        self.device = Device.objects.create()
        self.reset()

    def reset(self, device=None):
        """Backdate the stamp so any bump is unambiguous."""
        Device.objects.filter(pk=(device or self.device).pk).update(touched_at=LONG_AGO)

    def stamp(self, device=None):
        return Device.objects.get(pk=(device or self.device).pk).touched_at

    def assertBumped(self, device=None):
        self.assertGreater(self.stamp(device), LONG_AGO)

    def test_device_field_patch_bumps(self):
        res = self.client.patch(
            f"/api/v1/inventory/{self.device.pk}/",
            {"status": "disassembled_diagnosing"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertBumped()

    def test_device_note_write_bumps(self):
        res = self.client.post(
            "/api/v1/device-notes/",
            {"device": self.device.pk, "text": "intake fact"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertBumped()

    def test_repair_create_and_phase_patch_bump(self):
        repair = Repair.objects.create(device=self.device)
        self.assertBumped()
        self.reset()
        res = self.client.patch(
            f"/api/v1/repairs/{repair.pk}/",
            {"teardown_done_at": "2026-07-27T19:00:00Z"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertBumped()

    def test_repair_note_and_measurement_bump(self):
        repair = Repair.objects.create(device=self.device)
        note = repair.notes.get(position=0)
        self.reset()
        res = self.client.post(
            "/api/v1/notes/",
            {"repair": repair.pk, "phase": "diagnostics", "position": 1, "title": "Symptom", "text": "no LED"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertBumped()
        self.reset()
        res = self.client.post(
            "/api/v1/measurements/",
            {"note": note.pk, "what": "5V rail", "value": "4.98V"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertBumped()

    def test_media_upload_on_device_note_bumps(self):
        chunk = DeviceNote.objects.create(device=self.device, text="photos")
        self.reset()
        image = io.BytesIO(make_jpeg())
        image.name = "intake.jpg"
        res = self.client.post("/api/v1/media/", {"image": image, "device_note": chunk.pk})
        self.assertEqual(res.status_code, 201)
        self.assertBumped()

    def test_exit_bumps(self):
        res = self.client.post(
            "/api/v1/exits/",
            {"device": self.device.pk, "kind": "scrapped"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertBumped()

    def test_arrival_flip_bumps_shipped_units_only(self):
        purchase = Purchase.objects.create(total_price=Decimal("10.00"))
        shipped = Device.objects.create(purchase=purchase, status="shipped")
        acquired = Device.objects.create(purchase=purchase, status="reassembled_tested")
        self.reset(shipped)
        self.reset(acquired)
        res = self.client.post(f"/api/v1/purchases/{purchase.pk}/arrive/", {})
        self.assertEqual(res.status_code, 200)
        self.assertGreater(self.stamp(shipped), LONG_AGO)
        # Units past shipped aren't part of the flip — no phantom edit stamp.
        self.assertEqual(self.stamp(acquired), LONG_AGO)

    def test_write_on_one_device_leaves_others_alone(self):
        other = Device.objects.create()
        self.reset(other)
        self.client.post(
            "/api/v1/device-notes/",
            {"device": self.device.pk, "text": "mine"},
            content_type="application/json",
        )
        self.assertEqual(self.stamp(other), LONG_AGO)

    def test_payloads_expose_touched_at(self):
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertIn("touched_at", row)
        detail = self.client.get(f"/api/v1/inventory/{self.device.pk}/").json()
        self.assertIn("touched_at", detail)

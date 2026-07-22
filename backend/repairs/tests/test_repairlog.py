"""Bench-work behavior — the phase track, the completed-repair freeze, measurements."""

from django.test import TestCase
from django.utils import timezone

from repairs.models import Device, Repair


class PhaseTrackTests(TestCase):
    """current_phase = the phase after the LAST completed one — skips don't stall."""

    def setUp(self):
        self.repair = Repair.objects.create(device=Device.objects.create())

    def test_fresh_repair_starts_at_teardown(self):
        self.assertEqual(self.repair.current_phase, "teardown")

    def test_advances_past_completed_phases(self):
        self.repair.teardown_done_at = timezone.now()
        self.repair.wash_done_at = timezone.now()
        self.assertEqual(self.repair.current_phase, "repair")

    def test_skipped_phase_does_not_stall_the_track(self):
        # Teardown done, wash skipped, repair done → bench is at re-assemble.
        self.repair.teardown_done_at = timezone.now()
        self.repair.repair_done_at = timezone.now()
        self.assertEqual(self.repair.current_phase, "reassemble")

    def test_all_phases_done_is_completion_pending_not_complete(self):
        # Completion is MANUAL — checking every phase still leaves the mark to make.
        for key, _ in Repair.PHASES:
            setattr(self.repair, f"{key}_done_at", timezone.now())
        self.assertEqual(self.repair.current_phase, "completion")

    def test_verify_alone_reaches_completion_pending(self):
        self.repair.verify_done_at = timezone.now()
        self.assertEqual(self.repair.current_phase, "completion")

    def test_manual_completion_wins_regardless_of_phases(self):
        # Stopping before re-assembly and marking complete is a deliberate,
        # demonstrable statement that the unchecked phases did NOT happen.
        self.repair.repair_done_at = timezone.now()
        self.repair.completed_at = timezone.now()
        self.assertEqual(self.repair.current_phase, "complete")
        self.assertIsNone(self.repair.reassemble_done_at)

    def test_patch_completed_at(self):
        url = f"/api/v1/repairs/{self.repair.pk}/"
        res = self.client.patch(
            url,
            {"completed_at": timezone.now().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.repair.refresh_from_db()
        self.assertIsNotNone(self.repair.completed_at)
        self.assertEqual(self.repair.current_phase, "complete")

    def test_patch_endpoint_sets_and_clears_a_phase(self):
        url = f"/api/v1/repairs/{self.repair.pk}/"
        stamp = timezone.now().isoformat()

        res = self.client.patch(
            url, {"wash_done_at": stamp, "wash_note": "smoker unit — double dunk"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.repair.refresh_from_db()
        self.assertIsNotNone(self.repair.wash_done_at)
        self.assertEqual(self.repair.wash_note, "smoker unit — double dunk")

        res = self.client.patch(url, {"wash_done_at": None}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.repair.refresh_from_db()
        self.assertIsNone(self.repair.wash_done_at)

    def test_device_detail_payload_carries_phases(self):
        self.repair.teardown_done_at = timezone.now()
        self.repair.save()
        res = self.client.get(f"/api/v1/inventory/{self.repair.device_id}/")
        self.assertEqual(res.status_code, 200)
        payload = res.json()["repairs"][0]
        self.assertIsNotNone(payload["teardown_done_at"])
        self.assertEqual(payload["current_phase"], "wash")


class CompletedRepairFreezeTests(TestCase):
    """A completed repair rejects every write except toggling completed_at."""

    def setUp(self):
        self.repair = Repair.objects.create(
            device=Device.objects.create(), completed_at=timezone.now()
        )
        self.bucket = self.repair.notes.first()  # the standing "Measurements" note

    def test_phase_patch_rejected(self):
        res = self.client.patch(
            f"/api/v1/repairs/{self.repair.pk}/",
            {"wash_done_at": timezone.now().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_unmarking_completion_allowed(self):
        res = self.client.patch(
            f"/api/v1/repairs/{self.repair.pk}/",
            {"completed_at": None},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.repair.refresh_from_db()
        self.assertIsNone(self.repair.completed_at)

    def test_note_create_rejected(self):
        res = self.client.post(
            "/api/v1/notes/",
            {"repair": self.repair.pk, "position": 1, "title": "late entry"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_note_edit_rejected(self):
        res = self.client.patch(
            f"/api/v1/notes/{self.bucket.pk}/",
            {"title": "tampered"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_measurement_create_and_edit_rejected(self):
        res = self.client.post(
            "/api/v1/measurements/",
            {"note": self.bucket.pk, "what": "5V rail", "value": "5 V"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

        # Existing measurement (created pre-completion) also locked.
        self.repair.completed_at = None
        self.repair.save()
        m = self.bucket.measurements.create(what="DC jack", value="19 V")
        self.repair.completed_at = timezone.now()
        self.repair.save()
        res = self.client.patch(
            f"/api/v1/measurements/{m.pk}/",
            {"value": "tampered"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)


class MeasurementTests(TestCase):
    """Free-text measurements: created via API, nested under notes in the payload."""

    def setUp(self):
        self.repair = Repair.objects.create(device=Device.objects.create())
        self.note = self.repair.notes.create(position=1, title="Diagnose rail")

    def test_create_and_read_nested_in_device_payload(self):
        res = self.client.post(
            "/api/v1/measurements/",
            {"note": self.note.pk, "what": "5V rail", "value": "4.98 V", "comment": ""},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)

        payload = self.client.get(f"/api/v1/inventory/{self.repair.device_id}/").json()
        notes = payload["repairs"][0]["notes"]
        target = next(n for n in notes if n["title"] == "Diagnose rail")
        measurements = target["measurements"]
        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0]["what"], "5V rail")
        self.assertEqual(measurements[0]["value"], "4.98 V")

    def test_blank_value_allowed_what_required(self):
        # A failed measurement is a legit entry — the story lives in value/comment.
        res = self.client.post(
            "/api/v1/measurements/",
            {"note": self.note.pk, "what": "C701 ESR", "value": "", "comment": "pad lifted"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)

        res = self.client.post(
            "/api/v1/measurements/",
            {"note": self.note.pk, "what": "", "value": "5 V"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_patch_updates_in_place(self):
        m = self.note.measurements.create(what="DC jack", value="19 V")
        res = self.client.patch(
            f"/api/v1/measurements/{m.pk}/",
            {"value": "19.2 V under load"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        m.refresh_from_db()
        self.assertEqual(m.value, "19.2 V under load")

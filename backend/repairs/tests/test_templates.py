"""Per-phase notes + note templates (2026-07-28).

Notes live on a repair-substep; the Measurements bucket auto-creates on
Diagnostics. Templates are per (model × phase) config — one max — consumed by
the add-note modal; applying one is plain note-creation with nested
measurements, so the log never depends on the template surviving.
"""

from django.test import TestCase

from repairs.models import Device, NoteTemplate, Repair

from .helpers import make_ref


class NotePhaseTests(TestCase):
    def setUp(self):
        self.repair = Repair.objects.create(device=Device.objects.create())

    def test_measurements_bucket_auto_creates_on_diagnostics(self):
        bucket = self.repair.notes.get(position=0)
        self.assertEqual(bucket.title, "Measurements")
        self.assertEqual(bucket.phase, "diagnostics")

    def test_note_create_requires_phase(self):
        res = self.client.post(
            "/api/v1/notes/",
            {"repair": self.repair.pk, "position": 1, "title": "orphan"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_note_create_with_phase_and_nested_measurements(self):
        res = self.client.post(
            "/api/v1/notes/",
            {
                "repair": self.repair.pk,
                "phase": "diagnostics",
                "position": 1,
                "title": "Voltage readings",
                "measurements": [
                    {"what": "1.1V rail", "value": "1.09 V"},
                    {"what": "3.3V rail", "value": "3.28 V", "comment": "in spec"},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        note = self.repair.notes.get(title="Voltage readings")
        self.assertEqual(note.phase, "diagnostics")
        self.assertEqual(note.measurements.count(), 2)
        self.assertEqual(note.measurements.get(what="3.3V rail").comment, "in spec")

    def test_nested_measurements_rejected_on_edit(self):
        note = self.repair.notes.create(phase="repair", position=1, title="edit me")
        res = self.client.patch(
            f"/api/v1/notes/{note.pk}/",
            {"measurements": [{"what": "sneaky", "value": "1"}]},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(note.measurements.count(), 0)

    def test_subnote_inherits_parent_phase(self):
        parent = self.repair.notes.create(phase="repair", position=1, title="parent")
        res = self.client.post(
            "/api/v1/notes/",
            {
                "repair": self.repair.pk,
                "phase": "wash",  # wrong on purpose — parent's phase must win
                "parent": parent.pk,
                "position": 0,
                "title": "child",
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.repair.notes.get(title="child").phase, "repair")

    def test_note_payload_carries_phase(self):
        payload = self.client.get(
            f"/api/v1/inventory/{self.repair.device_id}/"
        ).json()
        self.assertEqual(payload["repairs"][0]["notes"][0]["phase"], "diagnostics")


class NoteTemplateTests(TestCase):
    def setUp(self):
        self.ref = make_ref(name="Xbox One S", brand="Microsoft", lane_name="console")

    def make_template(self):
        return self.client.post(
            "/api/v1/templates/",
            {
                "reference": self.ref.pk,
                "phase": "diagnostics",
                "name": "Voltage readings",
                "entries": [
                    {
                        "position": 0,
                        "title": "Standby rails",
                        "text": "",
                        "measurements": [
                            {"position": 0, "what": "1.1V rail", "expected": "1.1"},
                            {"position": 1, "what": "1.8V rail", "expected": "1.8"},
                            {"position": 2, "what": "3.3V rail", "expected": "3.3"},
                        ],
                    }
                ],
            },
            content_type="application/json",
        )

    def test_create_and_read_back(self):
        res = self.make_template()
        self.assertEqual(res.status_code, 201, res.content)
        body = self.client.get(f"/api/v1/templates/{res.json()['id']}/").json()
        self.assertEqual(body["name"], "Voltage readings")
        self.assertEqual(len(body["entries"][0]["measurements"]), 3)
        self.assertEqual(body["entries"][0]["measurements"][1]["expected"], "1.8")

    def test_entry_placeholder_round_trip(self):
        # text = real prefill; placeholder = ghost hint that never enters a note.
        res = self.client.post(
            "/api/v1/templates/",
            {
                "reference": self.ref.pk,
                "phase": "intake",
                "name": "Rev read",
                "entries": [
                    {"position": 0, "title": "Board Revision", "text": "",
                     "placeholder": "JDM-XXX", "measurements": []}
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = self.client.get(f"/api/v1/templates/{res.json()['id']}/").json()
        self.assertEqual(body["entries"][0]["placeholder"], "JDM-XXX")
        self.assertEqual(body["entries"][0]["text"], "")

    def test_one_template_per_reference_per_phase(self):
        self.assertEqual(self.make_template().status_code, 201)
        res = self.make_template()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(NoteTemplate.objects.count(), 1)

    def test_update_replaces_entries(self):
        template_id = self.make_template().json()["id"]
        res = self.client.patch(
            f"/api/v1/templates/{template_id}/",
            {
                "entries": [
                    {"position": 0, "title": "5V rail only", "text": "", "measurements": []}
                ]
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = self.client.get(f"/api/v1/templates/{template_id}/").json()
        self.assertEqual(len(body["entries"]), 1)
        self.assertEqual(body["entries"][0]["title"], "5V rail only")

    def test_delete_allowed_templates_are_config(self):
        template_id = self.make_template().json()["id"]
        res = self.client.delete(f"/api/v1/templates/{template_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(NoteTemplate.objects.count(), 0)

    def test_device_payload_carries_reference_templates(self):
        self.make_template()
        device = Device.objects.create(reference=self.ref)
        payload = self.client.get(f"/api/v1/inventory/{device.pk}/").json()
        self.assertEqual(payload["note_templates"][0]["name"], "Voltage readings")
        self.assertEqual(
            payload["note_templates"][0]["entries"][0]["measurements"][0]["what"],
            "1.1V rail",
        )

    def test_reference_filter(self):
        self.make_template()
        other = make_ref(name="DS4", brand="Sony", lane_name="controller")
        res = self.client.get(f"/api/v1/templates/?reference={other.pk}")
        self.assertEqual(res.json(), [])

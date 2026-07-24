"""Device lifecycle + bulk add — status lives on Device, never on phantom repairs."""

from decimal import Decimal

from django.test import TestCase

from repairs.models import Device, Location, Purchase

from .helpers import make_ref


class DeviceStatusTests(TestCase):
    """Status lives on Device; writing it never touches repairs."""

    def test_device_status_write_creates_no_phantom_repair(self):
        ref = make_ref(name="DS4", brand="Sony", lane_name="controller")
        res = self.client.post(
            "/api/v1/inventory/",
            {"reference": ref.pk, "status": "shipped"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        device = Device.objects.get(reference=ref)
        self.assertEqual(device.status, "shipped")
        self.assertEqual(device.repairs.count(), 0)

    def test_location_resolves_free_text_to_shared_lookup_row(self):
        for _ in range(2):
            res = self.client.post(
                "/api/v1/inventory/",
                {"location": "Shelf 1", "status": "shipped"},
                content_type="application/json",
            )
            self.assertEqual(res.status_code, 201)
        locations = Location.objects.filter(name="Shelf 1")
        self.assertEqual(locations.count(), 1)
        self.assertEqual(locations.first().devices.count(), 2)

    def test_patch_status(self):
        device = Device.objects.create()
        res = self.client.patch(
            f"/api/v1/inventory/{device.pk}/",
            {"status": "disassembled_solder"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.status, "disassembled_solder")
        self.assertEqual(device.repairs.count(), 0)

    def test_patch_rejects_retired_status(self):
        # The 2026-07-24 bench split retired the coarse states — the API must
        # not quietly accept them.
        device = Device.objects.create()
        res = self.client.patch(
            f"/api/v1/inventory/{device.pk}/",
            {"status": "in_repair"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_inventory_payload_carries_status(self):
        Device.objects.create(status="reassembled_tested")
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertEqual(row["status"], "reassembled_tested")
        self.assertEqual(row["status_display"], "Re-assembled: Tested")

    def test_repair_created_explicitly_with_measurements_bucket(self):
        device = Device.objects.create()
        res = self.client.post(
            "/api/v1/repairs/", {"device": device.pk}, content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(device.repairs.count(), 1)
        # Every repair carries the standing "Measurements" bucket note from birth.
        notes = device.repairs.first().notes.all()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].title, "Measurements")
        self.assertEqual(notes[0].position, 0)


class BulkAddTests(TestCase):
    """Bulk add spawns N identical skeletons from one purchase."""

    def test_bulk_create_links_purchase_reference_location_and_notes(self):
        purchase = Purchase.objects.create(total_price=Decimal("30.00"), expected_units=3)
        ref = make_ref(name="DS4", brand="Sony", lane_name="controller")
        res = self.client.post(
            "/api/v1/inventory/bulk/",
            {
                "purchase": purchase.pk,
                "location": "Shelf 2",
                "notes": "from the 3x lot",
                "lines": [{"reference": ref.pk, "quantity": 3}],
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["created"], 3)
        devices = Device.objects.filter(purchase=purchase)
        self.assertEqual(devices.count(), 3)
        for device in devices:
            self.assertEqual(device.reference, ref)
            self.assertEqual(device.location.name, "Shelf 2")
            self.assertEqual(device.notes, "from the 3x lot")
            self.assertEqual(device.status, "shipped")  # default
        self.assertEqual(purchase.unit_price, Decimal("10.00"))

    def test_bulk_create_rejects_zero_quantity(self):
        res = self.client.post(
            "/api/v1/inventory/bulk/",
            {"lines": [{"quantity": 0}]},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Device.objects.count(), 0)

    def test_bulk_create_heterogeneous_lot(self):
        # The 2-DS5 + 3-DS4 case: one call, per-line references.
        purchase = Purchase.objects.create(total_price=Decimal("100.00"), expected_units=5)
        ds5 = make_ref(name="DualSense", brand="Sony", lane_name="controller")
        ds4 = make_ref(name="DS4", brand="Sony", lane_name="controller")
        res = self.client.post(
            "/api/v1/inventory/bulk/",
            {
                "purchase": purchase.pk,
                "location": "Shelf 2",
                "lines": [
                    {"reference": ds5.pk, "quantity": 2},
                    {"reference": ds4.pk, "quantity": 3},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["created"], 5)
        self.assertEqual(Device.objects.filter(purchase=purchase, reference=ds5).count(), 2)
        self.assertEqual(Device.objects.filter(purchase=purchase, reference=ds4).count(), 3)

    def test_bulk_create_caps_total_units(self):
        res = self.client.post(
            "/api/v1/inventory/bulk/",
            {"lines": [{"quantity": 60}, {"quantity": 41}]},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Device.objects.count(), 0)

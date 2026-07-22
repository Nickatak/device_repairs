"""Price-sheet and phase-track behavior tests."""

import datetime
from decimal import Decimal

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from .models import CompPull, Device, DeviceReference, Lane, Location, Purchase, Repair
from .serializers import DeviceReferenceSerializer


def make_ref(name="Test Model", brand="TestBrand", lane_name="console"):
    lane, _ = Lane.objects.get_or_create(name=lane_name)
    return DeviceReference.objects.create(lane=lane, brand=brand, name=name)


class StaleGapTests(TestCase):
    """`stale` and `gap` implement the sheet's refresh discipline and gaps list."""

    def serialize(self, ref):
        return DeviceReferenceSerializer(
            DeviceReference.objects.select_related("lane")
            .prefetch_related("comp_pulls")
            .get(pk=ref.pk)
        ).data

    def test_no_pulls_is_gap_not_stale(self):
        data = self.serialize(make_ref())
        self.assertTrue(data["gap"])
        self.assertFalse(data["stale"])

    def test_recent_working_pull_is_neither(self):
        ref = make_ref()
        CompPull.objects.create(
            reference=ref, kind=CompPull.Kind.WORKING, pulled_on=timezone.localdate()
        )
        data = self.serialize(ref)
        self.assertFalse(data["gap"])
        self.assertFalse(data["stale"])

    def test_old_working_pull_is_stale(self):
        ref = make_ref()
        CompPull.objects.create(
            reference=ref,
            kind=CompPull.Kind.WORKING,
            pulled_on=timezone.localdate() - datetime.timedelta(days=61),
        )
        data = self.serialize(ref)
        self.assertTrue(data["stale"])
        self.assertFalse(data["gap"])

    def test_only_parts_pull_is_still_a_gap(self):
        # Parts/service comps don't satisfy the buy-decision refresh rule.
        ref = make_ref()
        CompPull.objects.create(
            reference=ref, kind=CompPull.Kind.PARTS, pulled_on=timezone.localdate()
        )
        data = self.serialize(ref)
        self.assertTrue(data["gap"])
        self.assertFalse(data["stale"])

    def test_latest_working_pull_wins_over_older(self):
        # A fresh re-pull clears staleness even though the old pull still exists.
        ref = make_ref()
        CompPull.objects.create(
            reference=ref,
            kind=CompPull.Kind.WORKING,
            pulled_on=timezone.localdate() - datetime.timedelta(days=200),
        )
        CompPull.objects.create(
            reference=ref, kind=CompPull.Kind.WORKING, pulled_on=timezone.localdate()
        )
        data = self.serialize(ref)
        self.assertFalse(data["stale"])


class CompPullGrainTests(TestCase):
    def test_one_pull_per_kind_per_day(self):
        ref = make_ref()
        today = timezone.localdate()
        CompPull.objects.create(reference=ref, kind=CompPull.Kind.WORKING, pulled_on=today)
        with self.assertRaises(IntegrityError):
            CompPull.objects.create(
                reference=ref, kind=CompPull.Kind.WORKING, pulled_on=today
            )

    def test_pulls_ordered_newest_first(self):
        ref = make_ref()
        today = timezone.localdate()
        old = CompPull.objects.create(
            reference=ref,
            kind=CompPull.Kind.WORKING,
            pulled_on=today - datetime.timedelta(days=30),
        )
        new = CompPull.objects.create(
            reference=ref, kind=CompPull.Kind.WORKING, pulled_on=today
        )
        self.assertEqual(list(ref.comp_pulls.all()), [new, old])


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
            {"status": "in_repair"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.status, "in_repair")
        self.assertEqual(device.repairs.count(), 0)

    def test_inventory_payload_carries_status(self):
        Device.objects.create(status="fixed")
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertEqual(row["status"], "fixed")
        self.assertEqual(row["status_display"], "Fixed")

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


class SeedPricesheetTests(TestCase):
    """The seed loads the real transcription file — these run against the real data."""

    def test_seed_is_idempotent(self):
        call_command("seed_pricesheet", verbosity=0)
        refs = DeviceReference.objects.count()
        pulls = CompPull.objects.count()
        lanes = Lane.objects.count()

        call_command("seed_pricesheet", verbosity=0)
        self.assertEqual(DeviceReference.objects.count(), refs)
        self.assertEqual(CompPull.objects.count(), pulls)
        self.assertEqual(Lane.objects.count(), lanes)

    def test_variant_split_replaces_old_row_and_repoints_devices(self):
        # Simulate the pre-split catalog: one "PS4 Slim" row with a device on it.
        old = make_ref(name="PS4 Slim", brand="Sony")
        device = Device.objects.create(reference=old)

        call_command("seed_pricesheet", verbosity=0)

        self.assertFalse(
            DeviceReference.objects.filter(brand="Sony", name="PS4 Slim").exists()
        )
        device.refresh_from_db()
        self.assertEqual(device.reference.name, "PS4 Slim (500GB)")

    def test_notes_marker_preserves_catalog_notes(self):
        # "PS4 (original)" carries notes_pricesheet in the JSON, so the marker section
        # must be appended below the catalog note — and must not stack on re-run.
        lane, _ = Lane.objects.get_or_create(name="console")
        DeviceReference.objects.create(
            lane=lane, brand="Sony", name="PS4 (original)", notes="Catalog one-liner."
        )
        call_command("seed_pricesheet", verbosity=0)
        call_command("seed_pricesheet", verbosity=0)

        row = DeviceReference.objects.get(brand="Sony", name="PS4 (original)")
        self.assertTrue(row.notes.startswith("Catalog one-liner."))
        self.assertEqual(row.notes.count("[price-sheet]"), 1)
        self.assertIn("HDMI = bread-and-butter", row.notes)

    def test_known_row_lands_with_stop_and_pull(self):
        call_command("seed_pricesheet", verbosity=0)
        row = DeviceReference.objects.get(brand="Acer", name="Predator XB271HU")
        self.assertEqual(row.lane.name, "monitor")
        self.assertEqual(str(row.stop_price), "50.00")
        pull = row.comp_pulls.filter(kind=CompPull.Kind.WORKING).first()
        self.assertIsNotNone(pull)
        self.assertEqual(str(pull.median), "150.00")
        self.assertEqual(pull.pulled_on.isoformat(), "2026-07-13")


class PurchaseTests(TestCase):
    """Money lives on the buy event; per-unit price is derived, never stored."""

    def test_create_purchase_resolves_source_and_links_devices(self):
        res = self.client.post(
            "/api/v1/purchases/",
            {
                "source": "eBay",
                "order_ref": "111-1231312",
                "total_price": "20.00",
                "expected_units": 4,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        purchase = Purchase.objects.get(order_ref="111-1231312")
        self.assertEqual(purchase.source.name, "eBay")
        res = self.client.post(
            "/api/v1/inventory/",
            {"purchase": purchase.pk, "status": "shipped"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(purchase.devices.count(), 1)

    def test_unit_price_prefers_expected_units_over_row_count(self):
        purchase = Purchase.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(purchase=purchase)  # only 1 of 4 rows entered so far
        self.assertEqual(purchase.unit_price, Decimal("5.00"))

    def test_unit_price_falls_back_to_linked_device_count(self):
        purchase = Purchase.objects.create(total_price=Decimal("30.00"))
        Device.objects.create(purchase=purchase)
        Device.objects.create(purchase=purchase)
        self.assertEqual(purchase.unit_price, Decimal("15.00"))

    def test_inventory_embeds_purchase_with_unit_price(self):
        purchase = Purchase.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(purchase=purchase, status="shipped")
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertEqual(row["purchase"]["unit_price"], "5.00")
        self.assertEqual(row["purchase"]["total_price"], "20.00")

    def test_parts_purchase_round_trips_kind_and_label(self):
        res = self.client.post(
            "/api/v1/purchases/",
            {
                "kind": "parts",
                "label": "DS4 hall module 20-pack",
                "source": "eBay",
                "total_price": "34.01",
                "expected_units": 20,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        purchase = Purchase.objects.get(label="DS4 hall module 20-pack")
        self.assertEqual(purchase.kind, "parts")
        self.assertEqual(str(purchase), "DS4 hall module 20-pack")
        # And it comes back typed on the list endpoint.
        row = next(
            r for r in self.client.get("/api/v1/purchases/").json() if r["id"] == purchase.pk
        )
        self.assertEqual(row["kind"], "parts")
        # Per-piece price still derives off expected_units.
        self.assertEqual(row["unit_price"], "1.70")

    def test_purchase_kind_defaults_to_device(self):
        res = self.client.post(
            "/api/v1/purchases/",
            {"source": "eBay", "order_ref": "22-00000-00001"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Purchase.objects.get(order_ref="22-00000-00001").kind, "device")

    def test_options_purchases_exclude_parts_kind(self):
        device_lot = Purchase.objects.create(order_ref="27-11111-11111")
        Purchase.objects.create(kind="parts", label="hall modules")
        ids = [p["id"] for p in self.client.get("/api/v1/options/").json()["purchases"]]
        self.assertEqual(ids, [device_lot.pk])


class BulkAddTests(TestCase):
    """Bulk add spawns N identical skeletons from one purchase."""

    def test_bulk_create_links_purchase_reference_location_and_notes(self):
        purchase = Purchase.objects.create(total_price=Decimal("30.00"), expected_units=3)
        ref = make_ref(name="DS4", brand="Sony", lane_name="controller")
        res = self.client.post(
            "/api/v1/inventory/bulk/",
            {
                "purchase": purchase.pk,
                "reference": ref.pk,
                "location": "Shelf 2",
                "notes": "from the 3x lot",
                "quantity": 3,
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
            {"quantity": 0},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Device.objects.count(), 0)


class SeedPurchasesTests(TestCase):
    """The tracking-CSV import: idempotent, source-splitting, ignore-respecting."""

    def test_import_is_idempotent_and_splits_sources(self):
        call_command("seed_purchases")
        count = Purchase.objects.count()
        self.assertGreater(count, 30)
        # The custody row (ignore flagged) never imports.
        self.assertFalse(Purchase.objects.filter(ledger_ref="0030").exists())
        # Marketplace cell splits into channel + refs: a long bare number is a
        # LISTING id (not stored — it survives only in the fallback URL).
        lot = Purchase.objects.get(ledger_ref="0004")
        self.assertEqual(lot.source.name, "eBay")
        self.assertEqual(lot.order_ref, "")
        self.assertEqual(lot.url, "https://www.ebay.com/itm/168422045256")
        self.assertEqual(lot.expected_units, 4)
        # Full combined form: the ORDER number wins the URL; seller → from_who.
        full = Purchase.objects.get(ledger_ref="0034")
        self.assertEqual(full.order_ref, "27-14860-22553")
        self.assertEqual(
            full.url, "https://order.ebay.com/ord/show?orderId=27-14860-22553"
        )
        self.assertEqual(full.from_who, "billnorseman22")
        # Non-marketplace cells alias to canonical channels (gifts = Friend;
        # pickup location detail moves to the note).
        gift = Purchase.objects.get(ledger_ref="0006")
        self.assertEqual(gift.source.name, "Friend")
        self.assertEqual(gift.order_ref, "")
        pickup = Purchase.objects.get(ledger_ref="0020")
        self.assertEqual(pickup.source.name, "Local Pickup")
        self.assertIn("Upland", pickup.note)
        call_command("seed_purchases")
        self.assertEqual(Purchase.objects.count(), count)


class SeedUnitsTests(TestCase):
    """The units import: idempotent, lot-linking, status/label mapping."""

    def test_import_links_lots_and_maps_statuses(self):
        call_command("seed_purchases")
        call_command("seed_units")
        count = Device.objects.count()
        self.assertGreater(count, 70)
        unit = Device.objects.get(ledger_ref="0004-1")
        self.assertEqual(unit.purchase.ledger_ref, "0004")
        self.assertEqual(unit.status, "exited")  # ledger "sold" folds into exited
        self.assertIn("[exit: sold]", unit.notes)
        self.assertEqual(unit.label, "DS4 v2 (CUH-ZCT2U)")
        self.assertIn("[bench label: CTRL_1]", unit.notes)
        # "in-repair" (CSV) → "in_repair" (enum).
        self.assertTrue(Device.objects.filter(status="in_repair").exists())
        # Multi-lot ledger_ids resolve: 0010 lives in purchase "0001;0010;0022".
        keyboard = Device.objects.get(ledger_ref="0010")
        self.assertEqual(keyboard.purchase.ledger_ref, "0001;0010;0022")
        # Lot arrival backfilled from earliest unit acquired date.
        self.assertEqual(str(Device.objects.get(ledger_ref="0004-2").purchase.arrived_on), "2026-06-08")
        call_command("seed_units")
        self.assertEqual(Device.objects.count(), count)

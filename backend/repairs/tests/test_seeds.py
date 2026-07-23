"""Seed-command behavior — the price-sheet and tracking-CSV imports run against real data."""

from django.core.management import call_command
from django.test import TestCase

from repairs.models import CompPull, Device, DeviceReference, Lane, Purchase

from .helpers import make_ref


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


class SeedRepairsTests(TestCase):
    """The converted bench logs: idempotent, phase-dated, note/measurement upserts."""

    def test_seed_is_idempotent_and_backdates(self):
        call_command("seed_purchases")
        call_command("seed_units")
        call_command("seed_repairs")
        from repairs.models import Measurement, Note, Repair

        repairs = Repair.objects.count()
        notes = Note.objects.count()
        measurements = Measurement.objects.count()
        self.assertGreater(repairs, 10)

        call_command("seed_repairs")
        self.assertEqual(Repair.objects.count(), repairs)
        self.assertEqual(Note.objects.count(), notes)
        self.assertEqual(Measurement.objects.count(), measurements)

        # A known conversion: 0017-2's POST read with its termination codes.
        repair = Repair.objects.get(device__ledger_ref="0017-2")
        self.assertEqual(repair.created_at.date().isoformat(), "2026-07-05")
        self.assertIsNotNone(repair.teardown_done_at)
        self.assertIsNone(repair.completed_at)  # still open
        post = repair.notes.get(title="POST-over-I2C read")
        self.assertIn("BOOT_SUCCESS", post.measurements.get().value)
        # Completed engagements carry the manual mark.
        self.assertIsNotNone(
            Repair.objects.get(device__ledger_ref="0027").completed_at
        )


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

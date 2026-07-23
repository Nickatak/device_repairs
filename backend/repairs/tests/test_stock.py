"""Stock domain — derived counts, recount semantics, revision validation, seeds."""

import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from repairs.models import (
    Device,
    Part,
    Purchase,
    Repair,
    Revision,
    StockIntake,
    StockItem,
)

from .helpers import make_ref


def make_parts_purchase(**kwargs):
    return Purchase.objects.create(kind=Purchase.Kind.PARTS, **kwargs)


class DerivedCountTests(TestCase):
    """count = last recount + intakes − draws since; edits self-heal; presence = None."""

    def setUp(self):
        self.item = StockItem.objects.create(
            name="DS4 hall modules", mode=StockItem.Mode.COUNTED
        )
        self.purchase = make_parts_purchase(label="hall 20-pack")

    def draw(self, quantity):
        device = Device.objects.create()
        repair = Repair.objects.create(device=device)
        note = repair.notes.get(position=0)  # the standing Measurements note
        return Part.objects.create(
            note=note, stock_item=self.item, name="hall module", quantity=quantity
        )

    def test_uncounted_item_reads_none_not_zero(self):
        # Intakes alone don't establish a base — pre-existing stock is unknown.
        StockIntake.objects.create(
            purchase=self.purchase, stock_item=self.item, quantity=20
        )
        self.assertIsNone(self.item.count)

    def test_count_derives_from_recount_intakes_and_draws(self):
        self.item.last_count = 10
        self.item.counted_at = timezone.now() - datetime.timedelta(days=1)
        self.item.save()
        StockIntake.objects.create(
            purchase=self.purchase, stock_item=self.item, quantity=20
        )
        self.draw(4)
        self.assertEqual(self.item.count, 26)

    def test_recount_supersedes_earlier_transactions(self):
        StockIntake.objects.create(
            purchase=self.purchase, stock_item=self.item, quantity=20
        )
        self.draw(4)
        # Physical recount AFTER those events: they're absorbed into the base.
        self.item.last_count = 30
        self.item.counted_at = timezone.now()
        self.item.save()
        self.assertEqual(self.item.count, 30)
        self.draw(2)
        self.assertEqual(self.item.count, 28)

    def test_intake_edit_self_heals(self):
        self.item.last_count = 0
        self.item.counted_at = timezone.now() - datetime.timedelta(days=1)
        self.item.save()
        intake = StockIntake.objects.create(
            purchase=self.purchase, stock_item=self.item, quantity=20
        )
        intake.quantity = 25
        intake.save()
        self.assertEqual(self.item.count, 25)

    def test_presence_item_has_no_count(self):
        jellybeans = StockItem.objects.create(
            name="M2.5 screws", mode=StockItem.Mode.PRESENCE, last_count=999
        )
        self.assertIsNone(jellybeans.count)


class StockApiTests(TestCase):
    def setUp(self):
        self.item = StockItem.objects.create(
            name="DS4 rubber sets 030/040", mode=StockItem.Mode.COUNTED
        )
        self.parts = make_parts_purchase(label="rubber order")
        self.devices = Purchase.objects.create(kind=Purchase.Kind.DEVICE)

    def test_recount_endpoint_sets_base_and_stamp(self):
        res = self.client.post(
            f"/api/v1/stock/{self.item.id}/recount/",
            {"count": 42},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.last_count, 42)
        self.assertIsNotNone(self.item.counted_at)

    def test_intake_rejects_device_purchases(self):
        res = self.client.post(
            "/api/v1/stock/intakes/",
            {"purchase": self.devices.id, "stock_item": self.item.id, "quantity": 5},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_list_carries_derived_count_and_fits(self):
        ref = make_ref(name="DualShock 4 (v2)", brand="Sony")
        rev = Revision.objects.create(reference=ref, name="JDM-055")
        self.item.fits_revisions.add(rev)
        self.item.last_count = 7
        self.item.counted_at = timezone.now()
        self.item.save()
        res = self.client.get("/api/v1/stock/")
        row = next(r for r in res.json() if r["id"] == self.item.id)
        self.assertEqual(row["count"], 7)
        self.assertIn("JDM-055", row["fits_revisions"][0]["name"])


class DeviceRevisionTests(TestCase):
    def setUp(self):
        self.ref = make_ref(name="DualShock 4 (v2)", brand="Sony")
        self.other = make_ref(name="DualSense (PS5)", brand="Sony")
        self.rev = Revision.objects.create(reference=self.ref, name="JDM-040")

    def test_device_takes_matching_revision(self):
        res = self.client.post(
            "/api/v1/inventory/",
            {"reference": self.ref.id, "revision": self.rev.id},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)

    def test_device_rejects_foreign_revision(self):
        res = self.client.post(
            "/api/v1/inventory/",
            {"reference": self.other.id, "revision": self.rev.id},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_reference_change_rejects_stale_revision(self):
        device = Device.objects.create(reference=self.ref, revision=self.rev)
        res = self.client.patch(
            f"/api/v1/inventory/{device.id}/",
            {"reference": self.other.id},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)


class SeedRevisionsTests(TestCase):
    def test_seed_is_idempotent_and_maps_families(self):
        make_ref(name="DualShock 4 (v1)", brand="Sony")
        make_ref(name="DualShock 4 (v2)", brand="Sony")
        make_ref(name="DualSense (PS5)", brand="Sony")

        call_command("seed_revisions")
        count = Revision.objects.count()
        self.assertEqual(count, 12)  # 4 + 3 + 5 on the three refs present

        revs = Revision.objects.filter(
            reference__name="DualShock 4 (v2)"
        ).values_list("name", flat=True)
        self.assertEqual(set(revs), {"JDM-040", "JDM-050", "JDM-055"})

        call_command("seed_revisions")
        self.assertEqual(Revision.objects.count(), count)

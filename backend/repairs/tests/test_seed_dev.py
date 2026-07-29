"""seed_dev — the dev-DB reset (2026-07-28, dock01 became sole canonical).

The load-bearing contract is the guard: the command must be impossible to run
on a real ledger (dock01), with no override path, while staying rerunnable
over its own TEST output.
"""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from repairs.models import CompPull, Device, Purchase, StockItem

from .helpers import make_ref


class SeedDevTests(TestCase):
    def setUp(self):
        # A matching catalog row so the reference-dependent branch (revision,
        # fits, comp pulls) is exercised — the dev DB always has the catalog.
        make_ref(name="DualShock 4 (v1)", brand="Sony", lane_name="controller")

    def run_seed(self):
        out = StringIO()
        call_command("seed_dev", stdout=out)
        return out.getvalue()

    def test_refuses_on_real_data(self):
        Device.objects.create(serial="ABC123")  # real-looking serial
        with self.assertRaises(CommandError):
            self.run_seed()
        # Nothing was wiped.
        self.assertEqual(Device.objects.count(), 1)

    def test_refuses_even_on_blank_serial(self):
        # Real devices often have no serial read yet — blank must count as real.
        Device.objects.create(serial="")
        with self.assertRaises(CommandError):
            self.run_seed()

    def test_seeds_and_reseeds_over_itself(self):
        self.run_seed()
        first_ids = set(Device.objects.values_list("id", flat=True))
        self.assertEqual(len(first_ids), 6)
        self.assertTrue(
            all(s.startswith("TEST-") for s in Device.objects.values_list("serial", flat=True))
        )
        self.assertEqual(Purchase.objects.count(), 2)
        self.assertEqual(StockItem.objects.count(), 2)
        self.assertEqual(CompPull.objects.count(), 2)
        self.assertIsNotNone(Device.objects.get(serial="TEST-0001").reference)

        # Rerun: previous TEST ledger is replaced, not duplicated.
        self.run_seed()
        self.assertEqual(Device.objects.count(), 6)
        self.assertTrue(first_ids.isdisjoint(
            set(Device.objects.values_list("id", flat=True))
        ))

    def test_ledger_content_is_labeled(self):
        self.run_seed()
        for note in Purchase.objects.values_list("note", flat=True):
            self.assertIn("TEST DATA", note)
        for note in CompPull.objects.values_list("note", flat=True):
            self.assertIn("TEST comp", note)

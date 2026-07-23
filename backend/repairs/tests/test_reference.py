"""Price-sheet catalog behavior — stale/gap worklists and comp-pull grain."""

import datetime

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from repairs.models import CompPull, DeviceReference, Issue
from repairs.serializers import DeviceReferenceSerializer

from .helpers import make_ref


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


class IssueTests(TestCase):
    """The symptom-decomposition table: category|fault|cause|verdict rows on the payload."""

    def test_reference_payload_carries_ordered_issues(self):
        ref = make_ref()
        ref.issues.create(
            category="Board", fault="Dead console, power OK", cause="APU BGA",
            verdict="avoid", position=2,
        )
        ref.issues.create(
            category="Display", fault="No signal", cause="HDMI port",
            verdict="buy", note="reworkable", position=1,
        )
        row = next(
            r for r in self.client.get("/api/v1/reference/").json() if r["id"] == ref.pk
        )
        self.assertEqual(
            [(i["category"], i["fault"], i["cause"], i["verdict"]) for i in row["issues"]],
            [
                ("Display", "No signal", "HDMI port", "buy"),
                ("Board", "Dead console, power OK", "APU BGA", "avoid"),
            ],
        )
        self.assertEqual(row["issues"][0]["note"], "reworkable")
        self.assertEqual(row["issues"][1]["verdict_display"], "Avoid — walk away")


class SeedIssuesTests(TestCase):
    """The issues seed: real data file, idempotent, keyed on (reference, fault, cause)."""

    def test_seed_is_idempotent_against_real_catalog(self):
        call_command("seed_reference", verbosity=0)
        call_command("seed_pricesheet", verbosity=0)
        call_command("seed_issues", verbosity=0)
        count = Issue.objects.count()
        self.assertGreater(count, 200)  # the hand-converted table is ~290 rows
        call_command("seed_issues", verbosity=0)
        self.assertEqual(Issue.objects.count(), count)
        # A known conversion survives round-trip with its verdict reasoning.
        rrod = Issue.objects.get(
            reference__name="Xbox 360 (Fat)", fault="RROD (three red lights)"
        )
        self.assertEqual(rrod.category, "Board")
        self.assertEqual(rrod.cause, "GPU/CPU BGA solder failure")
        self.assertEqual(rrod.verdict, "avoid")
        self.assertIn("Reflow is temporary", rrod.note)


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

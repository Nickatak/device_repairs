"""Price-sheet catalog behavior — stale/gap worklists and comp-pull grain."""

import datetime

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from repairs.models import CompPull, DeviceReference
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
    """The hot-issues quick-list: verdict-typed rows on the catalog payload."""

    def test_reference_payload_carries_ordered_issues(self):
        ref = make_ref()
        ref.issues.create(verdict="avoid", title="APU BGA", position=2)
        ref.issues.create(
            verdict="buy", title="HDMI port dead", note="reworkable", position=1
        )
        row = next(
            r for r in self.client.get("/api/v1/reference/").json() if r["id"] == ref.pk
        )
        self.assertEqual(
            [(i["verdict"], i["title"]) for i in row["issues"]],
            [("buy", "HDMI port dead"), ("avoid", "APU BGA")],
        )
        self.assertEqual(row["issues"][0]["note"], "reworkable")
        self.assertEqual(row["issues"][1]["verdict_display"], "Avoid — walk away")


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

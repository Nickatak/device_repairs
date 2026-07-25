"""Price-sheet catalog behavior — stale/gap worklists and comp-pull grain."""

import datetime

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from repairs.models import CompPull, DeviceReference, Issue, Revision, Variant
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


class VariantTests(TestCase):
    """Variants: identity rows on the base reference; pulls gain a variant scope."""

    def test_variant_pull_coexists_with_base_pull_same_day(self):
        ref = make_ref()
        gow = Variant.objects.create(reference=ref, name="Gears of War Edition")
        today = timezone.localdate()
        CompPull.objects.create(reference=ref, kind=CompPull.Kind.WORKING, pulled_on=today)
        CompPull.objects.create(
            reference=ref, variant=gow, kind=CompPull.Kind.WORKING, pulled_on=today
        )  # must not collide with the base pull
        with self.assertRaises(IntegrityError):
            CompPull.objects.create(
                reference=ref, variant=gow, kind=CompPull.Kind.WORKING, pulled_on=today
            )

    def test_variant_pull_does_not_satisfy_base_staleness(self):
        # A reference whose ONLY working pull is variant-scoped is still a gap.
        ref = make_ref()
        rose = Variant.objects.create(reference=ref, name="Rose Gold")
        CompPull.objects.create(
            reference=ref, variant=rose, kind=CompPull.Kind.WORKING,
            pulled_on=timezone.localdate(),
        )
        row = next(
            r for r in self.client.get("/api/v1/reference/").json() if r["id"] == ref.pk
        )
        self.assertTrue(row["gap"])
        self.assertEqual(row["variants"][0]["name"], "Rose Gold")
        self.assertEqual(row["comp_pulls"][0]["variant_name"], "Rose Gold")

    def test_duplicate_variant_name_rejected(self):
        ref = make_ref()
        Variant.objects.create(reference=ref, name="Pink")
        with self.assertRaises(IntegrityError):
            Variant.objects.create(reference=ref, name="Pink")


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


class RevisionApiTests(TestCase):
    """Revisions are the one writable catalog layer — bench work accretes rev
    knowledge (quirks, ID tells), so the API must support create + note edits."""

    def setUp(self):
        self.ref = make_ref(name="DualShock 4 (v2)")

    def test_create_revision(self):
        res = self.client.post(
            "/api/v1/revisions/",
            {"reference": self.ref.pk, "name": "JDM-040", "note": "v2 (CUH-ZCT2x).", "position": 0},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        rev = Revision.objects.get(pk=res.json()["id"])
        self.assertEqual(rev.reference, self.ref)
        self.assertEqual(rev.name, "JDM-040")

    def test_created_revision_appears_in_reference_payload(self):
        self.client.post(
            "/api/v1/revisions/",
            {"reference": self.ref.pk, "name": "JDM-050"},
            content_type="application/json",
        )
        payload = self.client.get("/api/v1/reference/").json()
        row = next(r for r in payload if r["id"] == self.ref.pk)
        self.assertEqual([rev["name"] for rev in row["revisions"]], ["JDM-050"])

    def test_patch_accretes_note(self):
        rev = Revision.objects.create(
            reference=self.ref, name="JDM-040", note="v2 (CUH-ZCT2x)."
        )
        res = self.client.patch(
            f"/api/v1/revisions/{rev.pk}/",
            {"note": "v2 (CUH-ZCT2x). No-battery boot loop on USB bench power."},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        rev.refresh_from_db()
        self.assertIn("boot loop", rev.note)
        self.assertEqual(rev.name, "JDM-040")  # untouched fields survive a PATCH

    def test_duplicate_name_on_same_reference_rejected_as_400(self):
        Revision.objects.create(reference=self.ref, name="JDM-040")
        res = self.client.post(
            "/api/v1/revisions/",
            {"reference": self.ref.pk, "name": "JDM-040"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_same_name_on_split_reference_allowed(self):
        # The DS4 catalog splits one platform across refs (30/31/149) — rev
        # sets duplicate across them by design, so uniqueness is per-ref only.
        other = make_ref(name="DualShock 4 (v1/v2 hall exit class)")
        Revision.objects.create(reference=self.ref, name="JDM-040")
        res = self.client.post(
            "/api/v1/revisions/",
            {"reference": other.pk, "name": "JDM-040"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)

    def test_delete_not_routed(self):
        rev = Revision.objects.create(reference=self.ref, name="JDM-040")
        res = self.client.delete(f"/api/v1/revisions/{rev.pk}/")
        self.assertEqual(res.status_code, 405)
        self.assertTrue(Revision.objects.filter(pk=rev.pk).exists())

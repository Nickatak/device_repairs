"""Seed the per-model hot-issues table from repairs/data/issues_seed.json.

Hand-converted (2026-07-22) from the reference notes' 'In-lane:/Avoid:/Common:'
prose into category | fault | cause | verdict | note rows. Idempotent: keyed on
(reference, fault, cause) — re-running refreshes category/verdict/note/position
and never duplicates. Rows added by hand on the site/admin with a different
(fault, cause) key are never touched; removals are manual.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import DeviceReference, Issue

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "issues_seed.json"


class Command(BaseCommand):
    help = "Seed/refresh per-model issues from repairs/data/issues_seed.json (idempotent)."

    def handle(self, *args, **options):
        with open(DATA_FILE, encoding="utf-8") as fh:
            rows = json.load(fh)

        created = updated = 0
        unmatched = []
        positions: dict[int, int] = {}
        for row in rows:
            ref = DeviceReference.objects.filter(
                brand=row["brand"], name=row["name"]
            ).first()
            if ref is None:
                unmatched.append(f"{row['brand']} {row['name']}")
                continue
            positions[ref.pk] = positions.get(ref.pk, 0) + 1
            _, made = Issue.objects.update_or_create(
                reference=ref,
                fault=row["fault"],
                cause=row["cause"],
                defaults={
                    "category": row["category"],
                    "verdict": row["verdict"],
                    "note": row["note"],
                    "position": positions[ref.pk],
                },
            )
            created += made
            updated += not made

        self.stdout.write(
            f"Done — issues: {created} created, {updated} refreshed "
            f"across {len(positions)} references."
        )
        for name in sorted(set(unmatched)):
            self.stdout.write(self.style.WARNING(f"  unmatched reference: {name}"))

"""Seed board revisions from repairs/data/revisions_seed.json.

Converted 2026-07-23 from references/ds4-rev-map.md in the learning repo (the
accreted teardown knowledge; that doc stays the narrative source — sharing-family
provenance, open experiments). Committed data: model numbers only, no PII.
Idempotent: upserts on (reference, name); revisions added via the site/admin on
other references are never touched. New revs accrete via admin, not this file.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import DeviceReference

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "revisions_seed.json"


class Command(BaseCommand):
    help = "Seed/refresh board revisions from repairs/data/revisions_seed.json (idempotent)."

    def handle(self, *args, **options):
        with open(DATA_FILE, encoding="utf-8") as fh:
            entries = json.load(fh)

        created = updated = 0
        unmatched = []
        for entry in entries:
            reference = DeviceReference.objects.filter(
                brand=entry["brand"], name=entry["name"]
            ).first()
            if reference is None:
                unmatched.append(f"{entry['brand']} {entry['name']}")
                continue
            for position, rev in enumerate(entry["revisions"]):
                _, was_created = reference.revisions.update_or_create(
                    name=rev["name"],
                    defaults={"note": rev["note"], "position": position},
                )
                created += was_created
                updated += not was_created

        self.stdout.write(
            f"Done — revisions: {created} created, {updated} refreshed."
        )
        for name in unmatched:
            self.stdout.write(self.style.WARNING(f"  unmatched reference: {name}"))

"""Seed stock buckets from repairs/data/stock_seed.json.

Hand-converted (2026-07-23) from tracking/parts/inventory.csv in the learning
repo, which froze at import — bucket counts and states live on the site from
then on (recount/intake/state-cycle, never the CSV). The JSON is gitignored
(order numbers in notes). Idempotent: buckets upsert on name; counted rows get
their CSV count as the recount base with the row's count/arrival date as the
stamp. fits links resolve natural keys (reference brand+name, revision name).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import DeviceReference, Revision, StockItem

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "stock_seed.json"


class Command(BaseCommand):
    help = "Seed/refresh imported stock buckets (idempotent on name)."

    def handle(self, *args, **options):
        with open(DATA_FILE, encoding="utf-8") as fh:
            entries = json.load(fh)

        created = updated = 0
        missing = []
        for entry in entries:
            item, was_created = StockItem.objects.update_or_create(
                name=entry["name"],
                defaults={
                    "category": entry["category"],
                    "mode": entry["mode"],
                    "state": entry["state"],
                    "last_count": entry["last_count"],
                    "counted_at": entry["counted_at"],
                    "note": entry["note"],
                },
            )
            created += was_created
            updated += not was_created

            refs = []
            for brand, name in entry["fits_references"]:
                ref = DeviceReference.objects.filter(brand=brand, name=name).first()
                if ref is None:
                    missing.append(f"{entry['name']} → ref {brand} {name}")
                else:
                    refs.append(ref)
            item.fits_references.set(refs)

            revs = []
            for brand, ref_name, rev_name in entry["fits_revisions"]:
                rev = Revision.objects.filter(
                    reference__brand=brand, reference__name=ref_name, name=rev_name
                ).first()
                if rev is None:
                    missing.append(f"{entry['name']} → rev {rev_name} ({ref_name})")
                else:
                    revs.append(rev)
            item.fits_revisions.set(revs)

        self.stdout.write(
            f"Done — stock buckets: {created} created, {updated} refreshed."
        )
        for m in missing:
            self.stdout.write(self.style.WARNING(f"  unresolved fit: {m}"))

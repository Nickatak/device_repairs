"""Seed the parts-order ledger from repairs/data/parts_seed.json.

Hand-converted (2026-07-23) from tracking/parts/orders.csv in the learning
repo, which froze at import — the site is canonical for parts orders from
then on. The JSON is gitignored (order numbers, seller handles); it exists
only on machines that hold the private data. Idempotent: rows upsert on their
synthetic ledger_ref ("parts-NN" = CSV row order; -64/-65 recovered from an
archive buy table the CSV census missed).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import Order, Source

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "parts_seed.json"


class Command(BaseCommand):
    help = "Seed/refresh the imported parts-order ledger (idempotent on ledger_ref)."

    def handle(self, *args, **options):
        with open(DATA_FILE, encoding="utf-8") as fh:
            entries = json.load(fh)

        created = updated = 0
        for entry in entries:
            source = (
                Source.objects.get_or_create(name=entry["source"])[0]
                if entry["source"]
                else None
            )
            _, was_created = Order.objects.update_or_create(
                ledger_ref=entry["ledger_ref"],
                defaults={
                    "kind": Order.Kind.PARTS,
                    "label": entry["label"],
                    "source": source,
                    "from_who": entry["from_who"],
                    "order_ref": entry["order_ref"],
                    "url": entry["url"],
                    "total_price": entry["total_price"],
                    # JSON key keeps its pre-rename name; the seed file is frozen.
                    "ordered_on": entry["purchased_on"],
                    "arrived_on": entry["arrived_on"],
                    "expected_units": entry["expected_units"],
                    "note": entry["note"],
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(
            f"Done — parts orders: {created} created, {updated} refreshed."
        )

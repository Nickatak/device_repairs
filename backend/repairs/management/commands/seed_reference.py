"""Seed the device-reference catalog from a curated JSON data file.

Idempotent: keyed on (brand, name) via update_or_create, so re-running refreshes the
catalog fields rather than duplicating. Data lives in repairs/data/device_reference_seed.json
— one object per known model. Consoles/controllers come from Nick's ~/learning/device_repair
docs; monitors and laptops were research-gathered with every release_year fetched from a web
source (the per-row `year_source` records provenance; this loader ignores it).

To extend the catalog, edit the JSON and re-run `python manage.py seed_reference`.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import DeviceReference, Lane

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "device_reference_seed.json"

# Only these keys map to model fields; anything else in the JSON (e.g. year_source) is ignored.
# The JSON's `category` key predates the Lane model and resolves to a lane row here.
FIELDS = ("model_numbers", "release_year", "configurations", "notes")


class Command(BaseCommand):
    help = "Seed/refresh the device-reference catalog from the JSON data file (idempotent)."

    def handle(self, *args, **options):
        rows = json.loads(DATA_FILE.read_text())

        created = 0
        updated = 0
        for row in rows:
            defaults = {k: row[k] for k in FIELDS}
            defaults["lane"] = Lane.objects.get_or_create(name=row["category"])[0]
            _, made = DeviceReference.objects.update_or_create(
                brand=row["brand"],
                name=row["name"],
                defaults=defaults,
            )
            if made:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {created} created, {updated} refreshed ({len(rows)} catalog rows)."
            )
        )

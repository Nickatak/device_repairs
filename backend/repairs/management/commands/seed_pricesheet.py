"""Seed the price sheet (lanes, catalog rows, comp pulls) from the curated JSON.

Idempotent: lanes keyed on name, references on (brand, name), comp pulls on
(reference, kind, pulled_on) — all via update_or_create, so re-running refreshes
rather than duplicates. Data lives in repairs/data/price_sheet_seed.json, transcribed
by hand from ~/learning/device_repair/references/prices.md (see docs/price-sheet.md).

Two conventions beyond the plain upsert:

- `notes_pricesheet`: merged into the row's `notes` under a "[price-sheet]" marker so
  catalog-seed notes (seed_reference) survive. Anything after the marker is replaced
  on re-run; anything before it is left alone.
- `replaces`: list of "Brand|Name" keys of old catalog rows this row supersedes
  (variant splits, e.g. "PS4 Slim" → 500GB + 1TB rows). Devices pointing at the old
  row are re-pointed at this one, then the old row is deleted.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from repairs.models import CompPull, DeviceReference, Lane

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "price_sheet_seed.json"

NOTES_MARKER = "[price-sheet]"

REFERENCE_FIELDS = ("sku_prefix", "memory_config", "stop_price", "stop_note", "release_year")
PULL_FIELDS = ("median", "p25", "p75", "n", "window_days", "velocity_per_day", "verified", "note")


def merged_notes(existing: str, sheet_notes: str) -> str:
    """Keep everything before the marker, replace everything after it."""
    base = existing.split(NOTES_MARKER)[0].rstrip()
    if not sheet_notes:
        return base
    section = f"{NOTES_MARKER}\n{sheet_notes}"
    return f"{base}\n\n{section}" if base else section


class Command(BaseCommand):
    help = "Seed/refresh the price sheet (lanes + catalog rows + comp pulls) — idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(DATA_FILE.read_text())

        lanes = {}
        for lane_row in data["lanes"]:
            lanes[lane_row["name"]], _ = Lane.objects.update_or_create(
                name=lane_row["name"], defaults={"policy": lane_row.get("policy", "")}
            )

        created = updated = pulls = replaced = 0
        for row in data["references"]:
            defaults = {k: row[k] for k in REFERENCE_FIELDS if k in row}
            defaults["lane"] = lanes.get(row["lane"]) or Lane.objects.get_or_create(name=row["lane"])[0]

            existing = DeviceReference.objects.filter(brand=row["brand"], name=row["name"]).first()
            defaults["notes"] = merged_notes(
                existing.notes if existing else "", row.get("notes_pricesheet", "")
            )

            ref, made = DeviceReference.objects.update_or_create(
                brand=row["brand"], name=row["name"], defaults=defaults
            )
            created += made
            updated += not made

            for old_key in row.get("replaces", []):
                old_brand, old_name = old_key.split("|", 1)
                old = (
                    DeviceReference.objects.filter(brand=old_brand, name=old_name)
                    .exclude(pk=ref.pk)
                    .first()
                )
                if old:
                    old.units.update(reference=ref)
                    old.delete()
                    replaced += 1

            for pull in row.get("comp_pulls", []):
                CompPull.objects.update_or_create(
                    reference=ref,
                    kind=pull.get("kind", CompPull.Kind.WORKING),
                    pulled_on=pull["pulled_on"],
                    defaults={k: pull[k] for k in PULL_FIELDS if k in pull},
                )
                pulls += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — lanes: {len(lanes)}; rows: {created} created, {updated} refreshed, "
                f"{replaced} replaced; comp pulls upserted: {pulls}."
            )
        )

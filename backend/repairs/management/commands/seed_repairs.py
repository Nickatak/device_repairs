"""Seed bench-log history from repairs/data/repairs_seed.json.

Hand-converted (2026-07-22) from the event-style prose that rode in device
notes before the site's Repair/Note/Measurement structure existed. Idempotent:
a device's seeded repair is matched by its backdated created date; notes upsert
on (repair, position), measurements on (note, what). Repairs the site created
on other dates are never touched. Identity data (serials, MACs) deliberately
stays in device notes, not here.
"""

import datetime
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import Device, Repair

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "repairs_seed.json"

PHASE_KEYS = [key for key, _ in Repair.PHASES]


def midday(date_str):
    """Date string → aware datetime at midday Pacific (19:00 UTC), matching
    how the conversion backdated events without recorded times."""
    d = datetime.date.fromisoformat(date_str)
    return datetime.datetime(d.year, d.month, d.day, 19, 0, tzinfo=datetime.timezone.utc)


class Command(BaseCommand):
    help = "Seed/refresh converted bench logs from repairs/data/repairs_seed.json (idempotent)."

    def handle(self, *args, **options):
        with open(DATA_FILE, encoding="utf-8") as fh:
            entries = json.load(fh)

        repairs_created = repairs_updated = 0
        unmatched = []
        for entry in entries:
            device = Device.objects.filter(ledger_ref=entry["ledger_ref"]).first()
            if device is None:
                unmatched.append(entry["ledger_ref"])
                continue
            spec = entry["repair"]
            created = midday(spec["created"])

            repair = next(
                (r for r in device.repairs.all() if r.created_at.date() == created.date()),
                None,
            )
            if repair is None:
                repair = Repair.objects.create(device=device)
                repairs_created += 1
            else:
                repairs_updated += 1
            # Set on the instance so the save() below persists it — auto_now_add
            # only fires on insert; a queryset-update here would be clobbered by
            # the instance's stale value at save time.
            repair.created_at = created

            for key in PHASE_KEYS:
                phase = spec.get("phases", {}).get(key)
                setattr(repair, f"{key}_done_at", midday(phase[0]) if phase else None)
                setattr(repair, f"{key}_note", phase[1] if phase else "")
            repair.completed_at = (
                midday(spec["completed"]) if spec.get("completed") else None
            )
            repair.save()

            for note_spec in spec["notes"]:
                note, _ = repair.notes.update_or_create(
                    position=note_spec["position"],
                    defaults={
                        "title": note_spec["title"],
                        "text": note_spec["text"],
                        "started_at": (
                            midday(note_spec["started"]) if note_spec.get("started") else None
                        ),
                    },
                )
                for m in note_spec.get("measurements", []):
                    note.measurements.update_or_create(
                        what=m["what"],
                        defaults={"value": m.get("value", ""), "comment": m.get("comment", "")},
                    )

        self.stdout.write(
            f"Done — bench logs: {repairs_created} repairs created, "
            f"{repairs_updated} refreshed."
        )
        for ref in unmatched:
            self.stdout.write(self.style.WARNING(f"  unmatched device: {ref}"))

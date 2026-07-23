"""Backfill Exit rows from the '[exit: kind]' note markers seed_units wrote.

Data reality at authoring (2026-07-22, verified against the live DB): 9 exited
devices, every one carrying a marker (5 parted, 1 sold, 1 gifted, 1 scrapped,
1 parted); Device.to_who was empty everywhere, so the 0033 field drop lost
nothing and this backfill parses notes only. The sold unit's money rides the
'[listed … · sold … · $N · fees $N]' detail marker (seed_units line: "exit
detail until Exit model lands" — this is that landing).

Device notes are read, never rewritten — the markers stay as historical text.
"""

import re

from django.db import migrations

EXIT_RE = re.compile(r"\[exit: ([a-z]+)\]")
SALE_MARKER_RE = re.compile(r"\[([^\]]*(?:listed|sold) \d{4}-\d{2}-\d{2}[^\]]*)\]")
SOLD_DATE_RE = re.compile(r"sold (\d{4}-\d{2}-\d{2})")
PRICE_RE = re.compile(r"(?<!fees )\$(\d+(?:\.\d+)?)")
FEES_RE = re.compile(r"fees \$(\d+(?:\.\d+)?)")

VALID_KINDS = {"sold", "gifted", "parted", "scrapped", "returned", "lost"}


def backfill(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    Exit = apps.get_model("repairs", "Exit")
    for device in Device.objects.filter(status="exited"):
        marker = EXIT_RE.search(device.notes or "")
        if not marker or marker.group(1) not in VALID_KINDS:
            continue  # no marker = no exit event on record; shows up as a fixup
        happened_on = sale_price = fees = None
        note = ""
        sale = SALE_MARKER_RE.search(device.notes)
        if sale:
            bits = sale.group(1)
            note = f"[backfilled from ledger marker: {bits}]"
            if m := SOLD_DATE_RE.search(bits):
                happened_on = m.group(1)
            if m := PRICE_RE.search(bits):
                sale_price = m.group(1)
            if m := FEES_RE.search(bits):
                fees = m.group(1)
        Exit.objects.create(
            device=device,
            kind=marker.group(1),
            happened_on=happened_on,
            sale_price=sale_price,
            fees=fees,
            note=note,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("repairs", "0033_remove_device_to_who_device_cost_override_exit"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]

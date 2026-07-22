"""Import buy events from the tracking ledger's devices/purchases.csv.

Snapshot import: copy the CSV from ~/learning/device_repair/tracking/devices/
into repairs/data/device_purchases.csv and re-run — idempotent, keyed on the
row's ledger_ids (stored as Purchase.ledger_ref), so re-running refreshes
imported rows and never duplicates. Purchases entered directly on the site
have a blank ledger_ref and are never touched.

Mapping (CSV → Purchase):
    ledger_ids → ledger_ref (natural key)
    date       → purchased_on
    qty        → expected_units
    cost       → total_price
    source     → Source lookup + order_ref (leading channel name split off;
                 remainder kept verbatim as the order reference)
    description + notes → note
    ignore (non-empty) → row skipped (mirrors reconcile.py semantics)

Lot category is not imported — it re-derives from the linked device rows.
"""

import csv
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import Purchase, Source

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "device_purchases.csv"

# Known marketplace channels — a source cell starting with one of these splits
# into channel + order reference ("eBay 168422045256"). Anything else ("Friend",
# "Local Pickup") is a channel name in full.
CHANNELS = ["eBay", "ShopGoodwill", "FB Marketplace", "Amazon", "AliExpress"]

# Canonical source names (Nick, 2026-07-21): gifts and friends are one channel;
# pickup location detail moves to the note, not the channel name.
ALIASES = {
    "Friend": ("Friend", None),
    "Gift (friend)": ("Friend", None),
    "Local pickup - Upland": ("Local Pickup", "Picked up in Upland"),
}


def split_source(cell):
    """Return (source_name, ref_text, extra_note) from the combined source cell."""
    cell = cell.strip()
    for channel in CHANNELS:
        if cell == channel:
            return channel, "", None
        if cell.startswith(channel + " "):
            return channel, cell[len(channel) :].strip(), None
    name, extra = ALIASES.get(cell, (cell, None))
    return name, "", extra


# eBay order numbers are XX-XXXXX-XXXXX-ish; the long bare number is a listing id.
ORDER_RE = re.compile(r"\d{2}-\d{4,6}-\d{5,7}")


def parse_refs(text):
    """Split a combined ref string into (order, listing, seller, residual).

    '158058425109 (order 27-14860-22553; seller billnorseman22)' →
    listing 158058425109, order 27-14860-22553, seller billnorseman22.
    Anything unrecognized ('auction', 'delivered') lands in residual for the note.
    """
    order = listing = seller = ""
    extras = []
    for group in re.findall(r"\(([^)]*)\)", text):
        for part in (p.strip() for p in group.split(";")):
            if part.startswith("order "):
                order = part[len("order ") :].strip()
            elif part.startswith("seller "):
                seller = part[len("seller ") :].strip()
            elif part:
                extras.append(part)
    outside = re.sub(r"\([^)]*\)", "", text).strip()
    rest = []
    for token in outside.split():
        if ORDER_RE.fullmatch(token) and not order:
            order = token
        elif token.isdigit() and len(token) >= 8 and not listing:
            listing = token
        elif token in ("item", "order"):
            continue  # bare prefixes ('item 1490…', 'order 16-…')
        else:
            rest.append(token)
    if rest:
        extras.insert(0, " ".join(rest))
    return order, listing, seller, "; ".join(extras)


def build_url(source_name, order, listing):
    """Best-effort link: the ORDER page when we have an order number (that's the
    receipt), listing page as fallback."""
    if source_name == "eBay":
        if order:
            return f"https://order.ebay.com/ord/show?orderId={order}"
        if listing:
            return f"https://www.ebay.com/itm/{listing}"
    if source_name == "ShopGoodwill" and listing:
        return f"https://shopgoodwill.com/item/{listing}"
    if source_name == "FB Marketplace" and listing:
        return f"https://www.facebook.com/marketplace/item/{listing}"
    return ""


class Command(BaseCommand):
    help = "Import buy events from repairs/data/device_purchases.csv (idempotent)."

    def handle(self, *args, **options):
        created = updated = skipped = 0
        with open(DATA_FILE, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("ignore") or "").strip():
                    skipped += 1
                    continue
                source_name, ref_text, extra_note = split_source(row["source"])
                source = (
                    Source.objects.get_or_create(name=source_name)[0]
                    if source_name
                    else None
                )
                order_ref, listing_ref, seller, residual = parse_refs(ref_text)
                note = row["description"].strip()
                if row["notes"].strip():
                    note += "\n" + row["notes"].strip()
                if extra_note:
                    note += "\n" + extra_note
                if residual:
                    note += f"\n[ref detail: {residual}]"
                _, made = Purchase.objects.update_or_create(
                    ledger_ref=row["ledger_ids"].strip(),
                    defaults={
                        "source": source,
                        "order_ref": order_ref,
                        "url": build_url(source_name, order_ref, listing_ref),
                        "from_who": seller,
                        "total_price": Decimal(row["cost"]),
                        "purchased_on": row["date"].strip() or None,
                        "expected_units": int(row["qty"]),
                        "note": note,
                    },
                )
                created += made
                updated += not made
        self.stdout.write(
            f"Done — purchases: {created} created, {updated} refreshed, {skipped} skipped (ignore)."
        )

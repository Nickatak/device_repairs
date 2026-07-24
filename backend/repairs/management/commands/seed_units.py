"""Import physical units from the tracking ledger's devices/units.csv.

Snapshot import, same flow as seed_purchases: copy the CSV into
repairs/data/device_units.csv and re-run — idempotent, keyed on the unit's
ledger id (stored as Device.ledger_ref). Site-entered devices (blank
ledger_ref) are never touched.

Mapping (CSV → Device):
    id       → ledger_ref (natural key); lot prefix links purchase ("0004-1" → 0004)
    model    → label (verbatim — unit specificity) + reference via MODEL_MAP
    status   → status ("in-repair" → "in_repair"; the rest match)
    fault / notes / label(bench) / listed / sold / sale_price / fees → notes
    acquired → backfills the lot's Purchase.arrived_on (earliest unit date) when unset
    ignore (non-empty) → row skipped

MODEL_MAP holds only unambiguous class matches; a unit whose variant is
genuinely unknown (storage-TBD One S, variant-TBD PS4/360) or off-catalog
(RAM sticks, docks) keeps reference NULL — its label carries the identity and
the reference is re-pointed on the device page once the variant is pinned.
Rev-TBD DS4 colorways map to the v1/v2 class row until a silkscreen read.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from repairs.models import Device, DeviceReference, Purchase

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "device_units.csv"

# The ledger's rich statuses fold into the site's five (Nick, 2026-07-21);
# exit reasons survive as '[exit: …]' note markers.
EXIT_STATUSES = {"sold", "parted", "scrapped", "gifted", "lost"}
STATUS_MAP = {
    # Post-2026-07-24 bench split: the frozen CSV's coarse states map to the
    # generic member of each family (this command is a historical import).
    "in-repair": "disassembled_diagnosing",
    "diagnosed": "acquired",
    "listed": "reassembled_tested",
    **{s: "exited" for s in EXIT_STATUSES},
}

DS4_V1 = ("Sony", "DualShock 4 (v1)")
DS4_V2 = ("Sony", "DualShock 4 (v2)")
DS4_CLASS = ("Sony", "DualShock 4 (v1/v2 hall exit class)")
DUALSENSE = ("Sony", "DualSense (PS5)")
XB1_PAD_OG = ("Microsoft", "Xbox One Wireless Controller (original)")
XB1_PAD_S = ("Microsoft", 'Xbox One Wireless Controller (2016 / "S")')
X360_PAD = ("Microsoft", "Xbox 360 Wireless Controller")
XB1S_AD = ("Microsoft", "Xbox One S All-Digital (1TB)")

MODEL_MAP = {
    "ASUS VG27AQ": ("ASUS", "VG27AQ"),
    "Acer Predator XB271HU": ("Acer", "Predator XB271HU"),
    "Apple iPhone 11": ("Apple", "iPhone 11"),
    "Ducky One 2 RGB TKL (#2 - the flawless unit)": ("Ducky", "One 2 RGB TKL"),
    "Ducky One 2 RGB TKL (learning board)": ("Ducky", "One 2 RGB TKL"),
    "DS4 v1 (CUH-ZCT1U)": DS4_V1,
    "DS4 v1 (CUH-ZCT1U, JDM-001)": DS4_V1,
    "DS4 v2 (CUH-ZCT2U)": DS4_V2,
    "DS4 v2 (CUH-ZCT2U) Jet Black": DS4_V2,
    "Sony DualShock 4 Blue-top/Black-bottom (v1 CUH-ZCT1x / JDM-030)": DS4_V1,
    "Sony DualShock 4 White (v1 CUH-ZCT1x / JDM-030)": DS4_V1,
    "Sony DualShock 4 MAGMA RED colorway (v2 CUH-ZCT2x / JDM-040)": DS4_V2,
    "Sony DualShock 4 MAGMA RED colorway (rev TBD - silkscreen read still open)": DS4_CLASS,
    "DS4 Jet Black (rev TBD)": DS4_CLASS,
    "DS4 Magma Red (rev TBD)": DS4_CLASS,
    "DS4 Gold (rev TBD)": DS4_CLASS,
    "DS4 Graffiti/patterned (rev TBD)": DS4_CLASS,
    "DS4 White (rev TBD)": DS4_CLASS,
    "DS4 Silver (rev TBD)": DS4_CLASS,
    "DS4 Green Camo (rev TBD)": DS4_CLASS,
    "DS4 Blue Camo (rev TBD)": DS4_CLASS,
    "DS4 Blueberry Blast (purple/blue; rev TBD)": DS4_CLASS,
    "Sony DualShock 3 (CECHZC2U)": ("Sony", "DualShock 3"),
    "DualSense (color/rev TBD)": DUALSENSE,
    "Sony DualSense (BDM rev TBD)": DUALSENSE,
    "Sony DualSense (rev TBD)": DUALSENSE,
    "Sony DualSense Galactic Purple": DUALSENSE,
    "Sony DualSense dark blue (rev TBD)": DUALSENSE,
    "Sony DualSense white (BDM rev TBD)": DUALSENSE,
    "Xbox 360 wireless (1403)": X360_PAD,
    "Xbox 360 wireless (variant TBD)": X360_PAD,
    "Xbox One 1537 (launch rev)": XB1_PAD_OG,
    # 1697 = 2015 pre-S rev (adds the jack, still no BT) — filed with 'original'.
    "Xbox One 1697 (2015 rev; 3.5mm jack)": XB1_PAD_OG,
    "Xbox One 1708": XB1_PAD_S,
    "Xbox One S gen (1708 - Bluetooth rev)": XB1_PAD_S,
    "Xbox One S All-Digital 1681": XB1S_AD,
    "Xbox One S 1681 All-Digital": XB1S_AD,
    "Toyota 89661-33350 (94 Camry V6)": ("Toyota", "89661 (90s ECU)"),
    "EasySMX ESM-9101 (third-party 2.4G pad)": None,
    "Forty4 GC801 (third-party 2.4G pad)": None,
    "HP Pavilion DV4-1287CL": None,  # catalog's Pavilion 15 (2019) is a different machine
    "Hynix 2GB PC3-12800U (HMT325U6CFR8C-PB)": None,
    "PlayStation 4 (variant TBD)": None,  # Original/Slim/Pro fork unresolved
    "PlayStation 4 (working donor)": None,
    "Samsung Galaxy S21 FE 5G (SM-G990U)": None,
    "Sony DualSense Galactic Purple (BDM-020)": DUALSENSE,
    "Toyota 0Z630 (2014 Corolla)": None,  # catalog's Toyota row is the 90s-ECU class
    "Xbox 360 (variant TBD)": None,  # Fat/Slim/E fork unresolved
    "ASUS DUAL-RTX4060-O8G (AD107 8GB)": None,  # only the 4060 husk class is cataloged
    "DualSense charging dock (brand/model TBD)": None,
    "DualSense charging dock (model TBD)": None,
    "Xbox One S (working donor)": None,  # storage tier unknown
    "Xbox One S 1681": None,  # storage tier unknown (0017-1/0017-2)
    "Xbox One S 1681 (disc/CD variant)": None,  # storage tier unknown
    "Xbox One S White 1681": None,  # storage tier unknown
}


def build_notes(row):
    parts = []
    if row["status"].strip() in EXIT_STATUSES:
        parts.append(f"[exit: {row['status'].strip()}]")
    if row["label"].strip():
        parts.append(f"[bench label: {row['label'].strip()}]")
    if row["fault"].strip():
        parts.append(f"Fault: {row['fault'].strip()}")
    if row["notes"].strip():
        parts.append(row["notes"].strip())
    sale_bits = [
        f"listed {row['listed'].strip()}" if row["listed"].strip() else None,
        f"sold {row['sold'].strip()}" if row["sold"].strip() else None,
        f"${row['sale_price'].strip()}" if row["sale_price"].strip() else None,
        f"fees ${row['fees'].strip()}" if row["fees"].strip() else None,
    ]
    sale_bits = [b for b in sale_bits if b]
    if sale_bits:
        parts.append(f"[{' · '.join(sale_bits)}]")  # exit detail until Exit model lands
    return "\n".join(parts)


class Command(BaseCommand):
    help = "Import physical units from repairs/data/device_units.csv (idempotent)."

    def handle(self, *args, **options):
        # Lot id → Purchase, via the semicolon lists in ledger_ref.
        lot_to_purchase = {}
        for purchase in Purchase.objects.exclude(ledger_ref=""):
            for lot in purchase.ledger_ref.split(";"):
                lot_to_purchase[lot.strip()] = purchase

        ref_cache = {}

        def resolve_ref(model_string):
            target = MODEL_MAP.get(model_string)
            if target is None:
                return None
            if target not in ref_cache:
                ref_cache[target] = DeviceReference.objects.filter(
                    brand=target[0], name=target[1]
                ).first()
            return ref_cache[target]

        created = updated = skipped = 0
        unmapped = set()
        arrivals = {}  # purchase → earliest unit acquired date
        with open(DATA_FILE, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("ignore") or "").strip():
                    skipped += 1
                    continue
                unit_id = row["id"].strip()
                lot = unit_id.split("-")[0]
                purchase = lot_to_purchase.get(lot)
                model_string = row["model"].strip()
                if model_string not in MODEL_MAP:
                    unmapped.add(model_string)
                reference = resolve_ref(model_string)
                acquired = row["acquired"].strip()
                if purchase and acquired:
                    prev = arrivals.get(purchase)
                    arrivals[purchase] = min(prev, acquired) if prev else acquired
                _, made = Device.objects.update_or_create(
                    ledger_ref=unit_id,
                    defaults={
                        "label": model_string,
                        "reference": reference,
                        "purchase": purchase,
                        "status": STATUS_MAP.get(row["status"], row["status"]),
                        "notes": build_notes(row),
                    },
                )
                created += made
                updated += not made

        backfilled = 0
        for purchase, date in arrivals.items():
            if purchase.arrived_on is None:
                purchase.arrived_on = date
                purchase.save()
                backfilled += 1

        self.stdout.write(
            f"Done — units: {created} created, {updated} refreshed, {skipped} skipped "
            f"(ignore); arrival dates backfilled on {backfilled} purchases."
        )
        for model_string in sorted(unmapped):
            self.stderr.write(f"UNMAPPED model string (imported with null reference): {model_string}")

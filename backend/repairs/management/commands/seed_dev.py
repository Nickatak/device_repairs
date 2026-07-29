"""Reset the LOCAL DEV database to a small, obviously-fake ledger.

dock01 became the sole canonical surface 2026-07-28 (dual-write retired);
localhost keeps the real catalog (references/revisions/issues, seeded from the
committed JSON) but its ledger is disposable TEST data so a stray edit can
never be mistaken for — or mistaken FOR — real bookkeeping.

Safety: this command REFUSES to run if any existing device has a serial that
doesn't start with TEST- (i.e. real data present). There is deliberately no
override flag — the first wipe of a real ledger must happen by hand, outside
this command, so it stays impossible to fire on the canonical DB.

Idempotent in the only way that matters: rerunning wipes the previous TEST
ledger and lays down a fresh one.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from repairs.models import (
    CompPull,
    Device,
    DeviceNote,
    DeviceReference,
    Location,
    Purchase,
    Source,
    StockIntake,
    StockItem,
)


class Command(BaseCommand):
    help = "Wipe the TEST ledger and reseed obvious dev data (refuses on real data)."

    def handle(self, *args, **options):
        real = Device.objects.exclude(serial__startswith="TEST-")
        if real.exists():
            raise CommandError(
                f"Refusing: {real.count()} device(s) with non-TEST serials exist "
                "(this looks like a real ledger). seed_dev has no override — "
                "wipe by hand first if you truly mean it."
            )

        with transaction.atomic():
            self._wipe()
            self._seed()

    def _wipe(self):
        # Ledger only — catalog (references/revisions/lanes/issues) and note
        # templates survive. Device delete cascades repairs/notes/exits/media;
        # purchase delete cascades stock intakes.
        Device.objects.all().delete()
        StockIntake.objects.all().delete()
        StockItem.objects.all().delete()
        Purchase.objects.all().delete()
        CompPull.objects.all().delete()
        self.stdout.write("wiped TEST ledger")

    def _seed(self):
        ref = DeviceReference.objects.filter(
            brand="Sony", name__startswith="DualShock 4 (v1)"
        ).first()
        revision = ref.revisions.filter(name__icontains="030").first() if ref else None

        source, _ = Source.objects.get_or_create(name="TEST source")
        bench, _ = Location.objects.get_or_create(name="TEST bench")

        lot = Purchase.objects.create(
            kind=Purchase.Kind.DEVICE,
            label="TEST lot — 4x DS4 (fake)",
            source=source,
            order_ref="TEST-ORDER-001",
            total_price=Decimal("40.00"),
            purchased_on=date(2026, 1, 1),
            arrived_on=date(2026, 1, 5),
            from_who="Test Seller",
            expected_units=4,
            note="TEST DATA — not a real purchase.",
        )
        parts_order = Purchase.objects.create(
            kind=Purchase.Kind.PARTS,
            label="TEST parts — hall modules 10pk",
            source=source,
            order_ref="TEST-ORDER-002",
            total_price=Decimal("12.00"),
            purchased_on=date(2026, 1, 2),
            arrived_on=date(2026, 1, 9),
            from_who="Test Seller",
            expected_units=10,
            note="TEST DATA — not a real purchase.",
        )

        statuses = [
            (Device.Status.SHIPPED, "TEST DS4 inbound"),
            (Device.Status.ACQUIRED, "TEST DS4 on shelf"),
            (Device.Status.DIS_DIAGNOSING, "TEST DS4 on bench"),
            (Device.Status.DIS_SOLDER, "TEST DS4 awaiting solder"),
            (Device.Status.AWAITING_EXIT, "TEST DS4 ready to list"),
            (Device.Status.EXITED, "TEST DS4 sold"),
        ]
        devices = []
        for i, (status, label) in enumerate(statuses, start=1):
            devices.append(
                Device.objects.create(
                    status=status,
                    label=label,
                    serial=f"TEST-{i:04d}",
                    reference=ref,
                    revision=revision if i == 3 else None,
                    location=bench,
                    purchase=lot if i <= 4 else None,
                )
            )

        DeviceNote.objects.create(
            device=devices[2],
            position=0,
            title="TEST unit note",
            text="Fake provenance chunk — dev data only.",
        )

        # Bench-active repair: intake+teardown done, sitting in diagnostics.
        repair = devices[2].repairs.create(
            intake_done_at="2026-01-06T10:00:00Z",
            teardown_done_at="2026-01-06T11:00:00Z",
        )
        bucket = repair.notes.get(position=0)  # auto-created Measurements
        bucket.measurements.create(what="TEST 3.3V rail", value="3.28 V")
        repair.notes.create(
            phase="intake", position=1, title="Shell Color", text="TEST black"
        )
        repair.notes.create(
            phase="repair", position=2, title="TEST hall mod L", text="fake work note"
        )

        devices[5].exits.create(
            kind="sold",
            happened_on=date(2026, 1, 20),
            sale_price=Decimal("34.99"),
            fees=Decimal("6.50"),
            to_who="Test Buyer",
            note="TEST DATA — not a real sale.",
        )

        halls = StockItem.objects.create(
            name="TEST hall modules",
            category="controller-parts",
            mode=StockItem.Mode.COUNTED,
            last_count=20,
            note="TEST DATA.",
        )
        if ref:
            halls.fits_references.add(ref)
        StockItem.objects.create(
            name="TEST rubber sets",
            category="controller-parts",
            mode=StockItem.Mode.PRESENCE,
            state=StockItem.State.IN_STOCK,
            note="TEST DATA.",
        )
        StockIntake.objects.create(
            purchase=parts_order, stock_item=halls, quantity=10, note="TEST intake."
        )

        if ref:
            CompPull.objects.create(
                reference=ref,
                kind=CompPull.Kind.WORKING,
                median=Decimal("45.00"),
                p25=Decimal("38.00"),
                p75=Decimal("52.00"),
                n=12,
                window_days=30,
                pulled_on=date(2026, 1, 15),
                note="TEST comp — fake numbers.",
            )
            CompPull.objects.create(
                reference=ref,
                kind=CompPull.Kind.PARTS,
                median=Decimal("15.00"),
                n=6,
                window_days=30,
                pulled_on=date(2026, 1, 15),
                note="TEST comp — fake numbers.",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"seeded: {len(devices)} devices, 2 purchases, 1 repair, "
                "1 exit, 2 stock items, 2 comp pulls — all TEST-labeled"
            )
        )

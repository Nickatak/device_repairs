"""Repair working-log domain model.

The shape and decisions behind these models live in ../../docs/domain.md (Settled tier).
The bench spine is Note: symptoms, faults, damage are observations *within* notes,
not nouns. Ledger spine: Purchase (money) → Device (unit) → Repair (bench work).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Source(models.Model):
    """Reusable channel a purchase came through (eBay, FB Marketplace, own stock).

    Thin lookup: money and order identity live on Purchase, not here.
    """

    name = models.CharField(max_length=120, unique=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    """Physical spot a unit lives in ('Shelf 1', 'bench', 'outbox') — free-text lookup."""

    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Purchase(models.Model):
    """A buy event at order/shipping-intake grain — MONEY LIVES HERE, not on Device.

    'ebay order 13-14739-66407, $37.87, 3x controllers' is ONE purchase; its units
    become Device rows as identity firms up on arrival (lot → exact models). The
    per-unit cost is derived — total split evenly across the lot — never stored.

    kind='parts' rows are the loose parts ledger (Nick's scoping 2026-07-21): the
    questions they answer are 'did I order this at some point' and 'has it arrived'
    — no stock counts, no line items. Nothing hangs off them; `label` is their
    identity and expected_units doubles as the piece count.
    """

    class Kind(models.TextChoices):
        DEVICE = "device", "Devices"
        PARTS = "parts", "Parts"
        # materials joins here when that CSV layer migrates.

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.DEVICE)
    label = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "One-line 'what is this' ('DS4 hall module 20-pack'). The identity of "
            "a parts purchase; optional color for device lots."
        ),
    )
    source = models.ForeignKey(
        Source, null=True, blank=True, on_delete=models.SET_NULL, related_name="purchases"
    )
    order_ref = models.CharField(
        max_length=200,
        blank=True,
        help_text="Order number ('27-14860-22553' on eBay). Blank for cash/local buys.",
    )
    url = models.URLField(
        blank=True,
        help_text=(
            "Link to the ORDER page (listing page only as fallback for old rows "
            "with no order number). Auto-built by the seed when the ids allow."
        ),
    )
    ledger_ref = models.CharField(
        max_length=60,
        blank=True,
        help_text=(
            "ledger_ids from the tracking CSV this row was imported from "
            "('0004', '0001;0010;0022'). Seed idempotency key; blank for "
            "purchases entered directly on the site."
        ),
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="What the whole lot cost. 0 = own stock; null = unknown.",
    )
    purchased_on = models.DateField(null=True, blank=True)
    arrived_on = models.DateField(
        null=True, blank=True, help_text="When the lot physically landed. Null = not yet / unknown."
    )
    from_who = models.CharField(
        max_length=120,
        blank=True,
        help_text="Who it came from — friend's name, seller handle ('billnorseman22').",
    )
    expected_units = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Units the lot should yield ('2x DS4' = 2). Used as the unit-price "
            "divisor while device rows are still being entered; blank = divide by "
            "actual linked devices."
        ),
    )
    note = models.TextField(
        blank=True, help_text="The lot as ordered ('2x DS4 controllers, untested')."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_on", "-id"]

    def __str__(self):
        if self.label:
            return self.label
        parts = [str(self.source) if self.source else None, self.order_ref or None]
        if self.total_price is not None:
            parts.append(f"${self.total_price}")
        return " ".join(p for p in parts if p) or f"purchase #{self.pk}"

    @property
    def unit_price(self):
        """Even split of the lot across its units; None while unknowable."""
        if self.total_price is None:
            return None
        n = self.expected_units or self.devices.count()
        if not n:
            return None
        return (self.total_price / n).quantize(Decimal("0.01"))


class Lane(models.Model):
    """Sourcing/repair lane — the price sheet's category grain (monitor, console, gpu…).

    Same free-text-lookup pattern as Source: adding a lane is a row, not a
    migration. `policy` holds the lane-wide prose that isn't per-model: buy policies,
    doctrine, service-lane comps, fee notes, lane conclusions.
    """

    name = models.CharField(max_length=60, unique=True, help_text="Lowercase slug style: 'monitor', 'gpu', 'test-equipment'.")
    policy = models.TextField(
        blank=True,
        help_text="Lane-level policy/doctrine prose (buy filters, lane conclusions, fee notes).",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DeviceReference(models.Model):
    """Catalog entry — 'what is this model?' plus its price-sheet row.

    Deliberately separate from the inventory table: Device rows track physical
    units on the bench; this answers "I see model X on a label — what year, what configs,
    what tends to break, and what would I pay for one". One row per thing-with-its-own-
    money: variants the markdown sheet compressed into one line (PS4 Slim 500GB / 1TB)
    are separate rows here. Class-grade rows ("27\" 1440p premium class") are legitimate
    entries with a blank brand.
    """

    lane = models.ForeignKey(Lane, on_delete=models.PROTECT, related_name="references")
    brand = models.CharField(
        max_length=120,
        blank=True,
        help_text="Manufacturer, e.g. Microsoft, Sony, ASUS. Blank for class-grade rows.",
    )
    name = models.CharField(
        max_length=160, help_text="Model name, e.g. 'Xbox One S', 'DualSense', 'VG27AQ'."
    )
    sku_prefix = models.CharField(
        max_length=255,
        blank=True,
        help_text="SKU/board-rev prefixes: 'CUH-20xx / 21xx / 22xx', 'JDM-040/050/055', 'A1466'.",
    )
    memory_config = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Harvest/donor decision string: '8GB GDDR5 unified, 256-bit, 16× 4Gb "
            "(clamshell)'. Deliberately unstructured."
        ),
    )
    model_numbers = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Comma-separated label/part numbers off the unit (e.g. '1708'). Often blank "
            "until seen on a real unit — the search box matches name + brand too."
        ),
    )
    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    configurations = models.TextField(
        blank=True, help_text="Common variants — storage tiers, disc vs digital, board revisions."
    )
    stop_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Max-buy ceiling for a symptom-decoded unit. Hand-set, never computed — "
            "the 1/3 rule informs it; mothballs and tuned stops override it. "
            "Null = no stop set (policy rows, harvest-exit rows)."
        ),
    )
    stop_note = models.TextField(
        blank=True,
        help_text="Reasoning + revision history ('$60→$50 2026-07-13; mothballed 2026-07-16').",
    )
    notes = models.TextField(blank=True, help_text="Signature fault / fix-vs-avoid one-liner.")

    class Meta:
        ordering = ["lane__name", "brand", "release_year", "name"]
        verbose_name = "device reference"
        verbose_name_plural = "device references"
        constraints = [
            models.UniqueConstraint(
                fields=["brand", "name"], name="unique_reference_brand_name"
            )
        ]

    def __str__(self):
        return f"{self.brand} {self.name}".strip()


class CompPull(models.Model):
    """One market observation for a catalog row. Append-only: current = latest.

    A new pull is a new row, never an edit of an old one — that's how revision history
    ('$150 → $134') stays free. Compound sheet cells that don't reduce to the structured
    fields land verbatim in `note` (zero-information-loss rule).
    """

    class Kind(models.TextChoices):
        WORKING = "working", "Working comp"
        PARTS = "parts", "Parts/for-parts tier"
        SERVICE = "service", "Service lane"
        OTHER = "other", "Other"

    class Verified(models.TextChoices):
        VERIFIED = "V", "Verified (sold/transaction data)"
        ESTIMATE = "E", "Estimate (cross-referenced, not solds)"

    reference = models.ForeignKey(
        DeviceReference, on_delete=models.CASCADE, related_name="comp_pulls"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.WORKING)
    median = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    p25 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    p75 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    n = models.PositiveIntegerField(null=True, blank=True, help_text="Sample size of the pull.")
    window_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Sold-window span the pull covered."
    )
    velocity_per_day = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Units/day where cleanly known; best-match floors stay in the note.",
    )
    verified = models.CharField(
        max_length=1, choices=Verified.choices, default=Verified.VERIFIED
    )
    pulled_on = models.DateField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-pulled_on", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["reference", "kind", "pulled_on"],
                name="one_pull_per_kind_per_day",
            )
        ]

    def __str__(self):
        value = f"${self.median}" if self.median is not None else "—"
        return f"{self.reference} {self.get_kind_display()}: {value} ({self.pulled_on})"


class Device(models.Model):
    """A physical unit, repairable more than once. Identity is best-effort.

    Identity comes from the `reference` link into the catalog (one-fact-one-place:
    brand/name/year/label numbers live there, not here). A dumpster board with an
    unclear model keeps reference null and leans on serial/notes.

    Carries the LIFECYCLE status (2026-07-21, mirrors the tracking-CSV ledger):
    where the unit sits from lead to exit. Manually set. Bench-work state lives on
    the Repair's phase track, not here.
    """

    class Status(models.TextChoices):
        # Five states (Nick, 2026-07-21 — 'diagnosed isn't actually a thing'):
        # inbound → on-hand → bench → done → gone. The exit REASON (sold/parted/
        # gifted…) lives in notes / exit detail, not as status positions.
        SHIPPED = "shipped", "Shipped (inbound)"
        ACQUIRED = "acquired", "Acquired"
        IN_REPAIR = "in_repair", "In repair"
        FIXED = "fixed", "Fixed"
        EXITED = "exited", "Exited"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACQUIRED,
        help_text="Lifecycle position, manually set — mirrors the tracking ledger.",
    )
    label = models.CharField(
        max_length=160,
        blank=True,
        help_text=(
            "Per-unit display name carrying unit specificity the catalog row can't "
            "('DS4 Gold (rev TBD)'). The reference is the CLASS identity; this is "
            "the unit's. Blank = display falls back to the reference."
        ),
    )
    ledger_ref = models.CharField(
        max_length=60,
        blank=True,
        help_text=(
            "Unit id from the tracking CSV this row was imported from ('0004-1'). "
            "Seed idempotency key; blank for devices entered directly on the site."
        ),
    )
    reference = models.ForeignKey(
        DeviceReference,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="units",
        help_text="Catalog entry for this model (year, configs, faults). Null = off-catalog.",
    )
    serial = models.CharField(max_length=120, blank=True)
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="devices",
        help_text="Where the unit physically sits right now ('Shelf 1'). Null = untracked.",
    )
    purchase = models.ForeignKey(
        Purchase,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="devices",
        help_text=(
            "The buy event this unit came from — source, order # and money live "
            "there. Null = found/own-stock without a buy record."
        ),
    )
    to_who = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Who the unit went to on exit — buyer, friend. Shares the counterparty "
            "pool with Purchase.from_who. Meaningful only when status is exited."
        ),
    )
    notes = models.TextField(
        blank=True, help_text="Facts about the unit, not any one step (e.g. 'uses a 19V brick')."
    )

    def __str__(self):
        if self.label:
            return self.label
        if self.reference_id:
            return str(self.reference)
        return self.serial or "(unidentified device)"


class Repair(models.Model):
    """One diagnose-and-fix engagement on one Device. Aggregate root of the log.

    Bench work moves through a FIXED phase track (2026-07-21 redesign):
    Teardown → Wash → Repair → Re-assemble → Verify. Each phase is a done-timestamp +
    optional deviation note; phases are skippable (a diagnosis-only job never washes).
    Freeform Notes + Measurements are the *contents of the Repair phase* — the one
    phase that's genuinely variable. Per-screw granularity belongs to the (parked)
    per-model teardown guide, not the log. The track ends at Verify: outflow states
    (listed / sold / shipped) are Device-lifecycle facts, not repair phases.

    No status field (removed 2026-07-21): the phase track IS the repair's state;
    the lifecycle lives on Device. A Repair exists only when bench work starts —
    never as a status carrier.

    `completed_at` is MANUAL and comes after Verify: marking a repair completed with
    phases unchecked is a deliberate, demonstrable statement that those phases did
    NOT happen (stopped before re-assembly, say) — not an oversight. Completion
    never requires checking everything.
    """

    PHASES = [
        ("teardown", "Teardown"),
        ("wash", "Wash"),
        ("repair", "Repair"),
        ("reassemble", "Re-assemble"),
        ("verify", "Verify"),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="repairs")
    comment = models.TextField(blank=True, help_text="Repair-level commentary (distinct from notes).")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Manual completion mark, after Verify. Unchecked phases on a completed "
            "repair demonstrably did NOT happen."
        ),
    )

    teardown_done_at = models.DateTimeField(null=True, blank=True)
    teardown_note = models.TextField(blank=True, help_text="Deviations only — the routine is not logged.")
    wash_done_at = models.DateTimeField(null=True, blank=True)
    wash_note = models.TextField(blank=True)
    repair_done_at = models.DateTimeField(null=True, blank=True)
    repair_note = models.TextField(blank=True, help_text="Summary only — the detail lives in Steps.")
    reassemble_done_at = models.DateTimeField(null=True, blank=True)
    reassemble_note = models.TextField(blank=True)
    verify_done_at = models.DateTimeField(null=True, blank=True)
    verify_note = models.TextField(blank=True, help_text="Function-validation evidence (tests run, results).")

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Every repair carries a standing "Measurements" note (position 0) — the
        # bucket for readings that belong to no specific notation. There's almost
        # always at least a bundle of measurements (Nick, 2026-07-21).
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            self.notes.create(position=0, title="Measurements")

    @property
    def current_phase(self):
        """Where the track stands: the phase after the last checked one.

        'complete' ONLY when completed_at is set (manual). 'completion' = phases
        exhausted but not yet marked — the next action is the mark itself. Skips
        count as done-with-nothing-to-say: with teardown and repair done but wash
        blank, the bench has moved on — current is re-assemble, not wash.
        """
        if self.completed_at:
            return "complete"
        keys = [key for key, _ in self.PHASES]
        done = [i for i, key in enumerate(keys) if getattr(self, f"{key}_done_at")]
        start = done[-1] + 1 if done else 0
        return keys[start] if start < len(keys) else "completion"

    def __str__(self):
        return f"Repair #{self.pk} — {self.device}"


class Note(models.Model):
    """The spine: one notation within a Repair, ordered. (Renamed from Step 2026-07-21.)

    Untyped: the old Type enum (test / observation / repair / notation) collapsed —
    a test produces an observation, logging it makes it a notation, and a corrective
    entry is equally a notation of work done (the phase track already marks that
    repair work happened). A note is a dated entry: title, text, measurements.
    Sub-notes allowed ONE level deep; deeper nesting means the approach went wrong.
    """

    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name="notes")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subnotes"
    )
    position = models.PositiveIntegerField(
        default=0, help_text="Ordering within the repair (or within a parent note)."
    )
    title = models.CharField(max_length=255, blank=True, help_text="Short heading for the note.")
    text = models.TextField(
        blank=True, help_text="The notation — what was tested / observed / done."
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, help_text="Note-scoped side commentary.")

    class Meta:
        ordering = ["position", "id"]

    def clean(self):
        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError("A note cannot be its own parent.")
            if self.parent.parent_id:
                raise ValidationError(
                    "Notes nest only one level deep — a sub-note cannot have sub-notes."
                )
            if self.parent.repair_id != self.repair_id:
                raise ValidationError("A sub-note must belong to the same repair as its parent.")

    def __str__(self):
        return self.title or self.text[:50]


class Measurement(models.Model):
    """Quick bench annotation on a Note: what was measured, and what it read.

    Simplified 2026-07-21 from the original structured shape (FK label lookup +
    decimal value + unit FK + expected nominal) — same grain-shift as the phase
    track: skill growth made free text the working unit. '5V rail' / '4.98 V'
    typed fast beats a four-field form. A failed measurement = the story in
    `value` or `comment` ('no reading — pad lifted').
    """

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="measurements")
    what = models.CharField(
        max_length=200, help_text="What was measured — '5V rail', 'C701 ESR', 'DC jack'."
    )
    value = models.CharField(
        max_length=120,
        blank=True,
        help_text="What it read — '4.98 V', '120 mΩ', 'no reading — pad lifted'.",
    )
    comment = models.TextField(
        blank=True, help_text="The 'why', or a provisional conclusion."
    )

    def __str__(self):
        return f"{self.what}: {self.value or '—'}"


class Part(models.Model):
    """Consumed into the board at a Note; counts toward the device's parts cost.

    A corrective note may record consumed Parts or none at all — 'fix' != 'install a part'.
    """

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="parts")
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quantity}× {self.name}"


class Media(models.Model):
    """Before/after & condition photos. Attaches to EITHER a Repair OR a Note (exactly one).

    The load-bearing case is condition documentation — photograph a pre-existing defect on
    intake so a later 'they broke my screen' claim is answered with the intake photo.
    """

    image = models.ImageField(upload_to="repair_media/")
    caption = models.CharField(max_length=255, blank=True)
    repair = models.ForeignKey(
        Repair, null=True, blank=True, on_delete=models.CASCADE, related_name="media"
    )
    note = models.ForeignKey(
        Note, null=True, blank=True, on_delete=models.CASCADE, related_name="media"
    )

    class Meta:
        verbose_name_plural = "media"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(repair__isnull=False, note__isnull=True)
                    | models.Q(repair__isnull=True, note__isnull=False)
                ),
                name="media_attaches_to_exactly_one_parent",
            )
        ]

    def clean(self):
        if bool(self.repair_id) == bool(self.note_id):
            raise ValidationError("Media must attach to exactly one of: a repair OR a note.")

    def __str__(self):
        return self.caption or f"Media #{self.pk}"

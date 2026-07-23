"""Price-sheet catalog — Lane (category grain), DeviceReference (model row), CompPull (market observation)."""

from django.db import models


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


class Issue(models.Model):
    """One row of a catalog model's symptom-decomposition table:
    category | fault | cause | verdict | note.

    The listing-scan question, structured: seller says <fault> — the cause
    column says what that decodes to, the verdict says buy (in-lane, I fix
    this class) / avoid (walk away) / caution (read the note). Seeded from
    repairs/data/issues_seed.json (seed_issues command, hand-converted from
    the notes prose 2026-07-22); the prose stays free-form color, never the
    fact of record for verdicts.
    """

    class Verdict(models.TextChoices):
        BUY = "buy", "Buy — in-lane fault"
        AVOID = "avoid", "Avoid — walk away"
        CAUTION = "caution", "Caution — read the note"

    reference = models.ForeignKey(
        DeviceReference, on_delete=models.CASCADE, related_name="issues"
    )
    category = models.CharField(
        max_length=40,
        blank=True,
        help_text="Subsystem grouping — Power, Display, Board, Input, Intake…",
    )
    fault = models.CharField(
        max_length=120,
        help_text="The symptom as a listing shows it — 'No power', 'RROD', 'Stick drift'.",
    )
    cause = models.CharField(
        max_length=200,
        blank=True,
        help_text="What the symptom decodes to — 'PSU / 5V MOSFET', 'APU BGA'.",
    )
    verdict = models.CharField(max_length=10, choices=Verdict.choices)
    note = models.TextField(
        blank=True,
        help_text="The detail behind the verdict ('reflow is temporary — walk away as a flip').",
    )
    position = models.PositiveIntegerField(
        default=0, help_text="Manual ordering within the reference's list."
    )

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"[{self.verdict}] {self.fault} → {self.cause or '?'} — {self.reference}"


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

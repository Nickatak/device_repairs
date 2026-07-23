"""Parts stock — the join between purchases (money in) and bench Parts (consumption).

A StockItem is a MINTED SKU (Nick's 2026-07-23 design session): clone parts have
no meaningful manufacturer numbers, so the bucket's identity is our own name for
it, at the grain it's CONSUMED at the bench (rubber SETS, not pieces — piece-level
interchangeability is a note on the bucket, not more buckets; split a bucket only
when consumption reality forces it).

Two tracking tiers, chosen per bucket:
- counted:  the number gates decisions (halls = throughput odometer, rev-specific
  daughterboards, open-gate checks). Counting is TRANSACTIONAL — intakes add,
  bench Part draws subtract, a physical recount overrides. The live count is
  DERIVED (last_count + intakes − draws since counted_at), never mutated in
  place, so edits to any intake/draw self-heal.
- presence: jellybeans. have/low/out set by eyeball (two-bin kanban); no
  arithmetic ever. Keep the counted tier small — every counted SKU is a
  recount obligation.
"""

from django.db import models

from .purchases import Purchase
from .reference import DeviceReference, Revision


class StockItem(models.Model):
    class Mode(models.TextChoices):
        COUNTED = "counted", "Counted"
        PRESENCE = "presence", "Presence (have/low/out)"

    class State(models.TextChoices):
        IN_STOCK = "in_stock", "In stock"
        LOW = "low", "Low"
        OUT = "out", "Out"

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="The minted SKU name, at consumption grain: 'DS4 rubber set, 030/040 family'.",
    )
    category = models.CharField(
        max_length=60,
        blank=True,
        help_text="Free-text grouping matching the purchase ledger: 'controller-parts', 'connectors'.",
    )
    note = models.TextField(
        blank=True,
        help_text=(
            "Compatibility prose and bucket knowledge — 'XSTC + D-pad pieces "
            "interchange across families; home button is family-specific'."
        ),
    )
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.PRESENCE)
    state = models.CharField(
        max_length=10,
        choices=State.choices,
        default=State.IN_STOCK,
        help_text="Presence-tier state, set by eyeball. Ignored for counted items.",
    )
    last_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Counted tier: the last PHYSICAL recount. Null = never counted.",
    )
    counted_at = models.DateTimeField(
        null=True, blank=True, help_text="When that recount happened."
    )
    fits_references = models.ManyToManyField(
        DeviceReference,
        blank=True,
        related_name="stock_items",
        help_text="Models this bucket serves rev-agnostically ('Xbox 360 controller').",
    )
    fits_revisions = models.ManyToManyField(
        Revision,
        blank=True,
        related_name="stock_items",
        help_text="Rev-specific fits ('JDS-055 daughterboards'). Empty both = universal/unknown.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name

    @property
    def count(self):
        """Live count for counted items: last recount + intakes − draws since.

        None for presence items and never-counted items — an uncounted counted
        item shows as unknown, not zero (intakes alone don't establish a base:
        the bucket may have had stock before its first recorded intake).
        """
        if self.mode != self.Mode.COUNTED or self.last_count is None:
            return None
        intakes = self.intakes.all()
        draws = self.draws.all()
        if self.counted_at is not None:
            intakes = [i for i in intakes if i.created_at > self.counted_at]
            draws = [d for d in draws if d.created_at > self.counted_at]
        return (
            self.last_count
            + sum(i.quantity for i in intakes)
            - sum(d.quantity for d in draws)
        )


class StockIntake(models.Model):
    """Units entering a bucket from a purchase — one purchase can feed many
    buckets (an 8-bag daughterboard order = 4 SKUs × 20)."""

    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="stock_intakes"
    )
    stock_item = models.ForeignKey(
        StockItem, on_delete=models.CASCADE, related_name="intakes"
    )
    quantity = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"+{self.quantity} → {self.stock_item} (from {self.purchase})"

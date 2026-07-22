"""Purchases ledger — money enters here. Purchase (the buy event) + Source (channel lookup)."""

from decimal import Decimal

from django.db import models


class Source(models.Model):
    """Reusable channel a purchase came through (eBay, FB Marketplace, own stock).

    Thin lookup: money and order identity live on Purchase, not here.
    """

    name = models.CharField(max_length=120, unique=True)
    note = models.TextField(blank=True)

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

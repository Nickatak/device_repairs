"""Physical inventory — Device (the unit on the bench/shelf) + Location (where it sits)."""

from django.db import models

from .purchases import Purchase
from .reference import DeviceReference


class Location(models.Model):
    """Physical spot a unit lives in ('Shelf 1', 'bench', 'outbox') — free-text lookup."""

    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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

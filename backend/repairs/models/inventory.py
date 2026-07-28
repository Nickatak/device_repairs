"""Physical inventory — Device (the unit on the bench/shelf) + Location (where it sits)."""

from django.db import models
from django.utils import timezone

from django.core.exceptions import ValidationError

from .purchases import Purchase
from .reference import DeviceReference, Revision


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
        # Two-family bench split (Nick, 2026-07-24, replacing in_repair/fixed):
        # the Disassembled family is PHYSICAL — it enumerates what's open on the
        # desk — with the sub-state naming what the unit is WAITING FOR (not
        # whether it's blocked). Re-assembled = shell closed; tested is the old
        # "fixed". A force-parked unit (shell closed mid-repair, open-gate rule)
        # leaves the Disassembled family — its pending work lives in notes.
        # The exit REASON (sold/parted/gifted…) stays in exit detail, not here.
        SHIPPED = "shipped", "Shipped (inbound)"
        ACQUIRED = "acquired", "Acquired"
        DIS_DIAGNOSING = "disassembled_diagnosing", "Disassembled: Diagnosing"
        DIS_PARTS = "disassembled_parts", "Disassembled: Parts"
        DIS_SOLDER = "disassembled_solder", "Disassembled: Solder"
        RE_UNTESTED = "reassembled_untested", "Re-assembled: Untested"
        RE_TESTED = "reassembled_tested", "Re-assembled: Tested"
        EXITED = "exited", "Exited"

    status = models.CharField(
        max_length=40,
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
    revision = models.ForeignKey(
        Revision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="units",
        help_text=(
            "Board revision, once read off the silkscreen (JDM-040). Must belong "
            "to this device's reference. Null = not yet identified."
        ),
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
    cost_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Explicit unit cost for mixed lots (2 DS5 + 3 DS4 shouldn't split "
            "evenly). Units without one split the lot's remainder evenly. "
            "Null = derive from the purchase."
        ),
    )
    touched_at = models.DateTimeField(
        auto_now=True,
        help_text=(
            "Last edit anywhere in the unit's tree — device fields, unit notes, "
            "repairs and their notes/measurements/parts/photos, exits. Child "
            "models bump it via Device.touch()."
        ),
    )

    @classmethod
    def touch(cls, device_id):
        """Stamp touched_at without firing save() — the child-write bump."""
        cls.objects.filter(pk=device_id).update(touched_at=timezone.now())

    def clean(self):
        if self.revision_id and self.revision.reference_id != self.reference_id:
            raise ValidationError(
                "Revision must belong to this device's reference."
            )

    @property
    def unit_cost(self):
        """What this unit cost: the override when set, else the lot's even share."""
        if self.cost_override is not None:
            return self.cost_override
        if self.purchase_id:
            return self.purchase.unit_price
        return None

    def __str__(self):
        if self.label:
            return self.label
        if self.reference_id:
            return str(self.reference)
        return self.serial or "(unidentified device)"


class DeviceNote(models.Model):
    """Unit-grain fact, one chunk per entry (replaced the Device.notes blob 2026-07-27).

    The device-scoped counterpart of the repair Note: facts about the unit that
    outlive any one repair (provenance, colorway questions, 'uses a 19V brick')
    accrete as dated chunks instead of re-editing one text field. Deliberately
    thinner than Note — no nesting, no measurements: bench observations belong
    on a Repair. Photos attach (intake/listing shots predate any repair).
    """

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="device_notes")
    position = models.PositiveIntegerField(
        default=0, help_text="Ordering on the device page; ties resolve by id (creation order)."
    )
    title = models.CharField(max_length=255, blank=True, help_text="Short heading for the chunk.")
    text = models.TextField(blank=True, help_text="The fact — unit-grain, not bench-step-grain.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Device.touch(self.device_id)

    def __str__(self):
        return self.title or self.text[:50]

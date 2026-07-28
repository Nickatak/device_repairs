"""Exits — money leaves here. One row per departure event on a Device.

The money mirror of purchases.py: Purchase (money in) → Device → Exit (money out).
A device usually exits once, but a return-then-resell is two events — that's why
this is a model, not fields on Device. Creating an exit via the API also flips
the device's lifecycle status to exited (mirrors the ledger rule: a unit exit =
status flip + exits row).
"""

from django.db import models

from .inventory import Device


class Exit(models.Model):
    class Kind(models.TextChoices):
        SOLD = "sold", "Sold"
        GIFTED = "gifted", "Gifted"
        PARTED = "parted", "Parted out"
        SCRAPPED = "scrapped", "Scrapped"
        RETURNED = "returned", "Returned (refund)"
        LOST = "lost", "Lost"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="exits")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    happened_on = models.DateField(
        null=True, blank=True, help_text="When the unit left. Null = date unknown."
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Money received — gross sale, or the refund on a returned kind. Null for gift/scrap.",
    )
    fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Resale costs — marketplace fee + outbound shipping.",
    )
    to_who = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Who the unit went to — buyer, friend. Shares the counterparty pool "
            "with Purchase.from_who."
        ),
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-happened_on", "-id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Device.touch(self.device_id)

    @property
    def net(self):
        """Money actually kept: sale_price − fees. None when no money changed hands."""
        if self.sale_price is None:
            return None
        return self.sale_price - (self.fees or 0)

    def __str__(self):
        money = f" ${self.sale_price}" if self.sale_price is not None else ""
        return f"{self.get_kind_display()}{money} — {self.device}"

"""Purchase lands: money and source move from Device to the buy event.

Hand-written (create → data-copy → remove must be ordered). Each device with a
source or price gets a Purchase built from its own row. Data cleanups, all
evidence-backed from the rows themselves:

- Source lookup dedup: "ebay" → "eBay", "Own" → "Own stock".
- Device 7's source was a pasted eBay order URL — becomes source "eBay" +
  order_ref extracted from the URL (URL kept in the purchase note);
  expected_units=3 per its "3x Controllers" note.
- Device 5's notes held a bare order number — moved to order_ref.
- Source rows left orphaned by the dedup are deleted.
"""

import re

import django.db.models.deletion
from django.db import migrations, models

SOURCE_ALIASES = {"ebay": "eBay", "Own": "Own stock"}


def build_purchases(apps, schema_editor):
    Device = apps.get_model("repairs", "Device")
    Purchase = apps.get_model("repairs", "Purchase")
    Source = apps.get_model("repairs", "Source")

    for device in Device.objects.select_related("source").order_by("id"):
        if device.source_id is None and device.acquisition_price is None:
            continue
        name = device.source.name if device.source else ""
        order_ref = ""
        note = ""
        expected = None
        if name.startswith("http"):
            note = name
            match = re.search(r"orderId=([\d-]+)", name)
            order_ref = match.group(1) if match else ""
            name = "eBay"
            if "3x Controllers" in device.notes:
                expected = 3
        name = SOURCE_ALIASES.get(name, name)
        if device.notes.strip() == "19-14706-54121":
            order_ref = device.notes.strip()
            device.notes = ""
        source = Source.objects.get_or_create(name=name)[0] if name else None
        device.purchase = Purchase.objects.create(
            source=source,
            order_ref=order_ref,
            total_price=device.acquisition_price,
            expected_units=expected,
            note=note,
        )
        device.save()

    Source.objects.filter(purchases__isnull=True).delete()


class Migration(migrations.Migration):
    # Data writes + ALTER on repairs_device can't share a transaction (Postgres
    # pending-trigger rule, same as 0019); the data step is re-runnable.
    atomic = False

    dependencies = [
        ("repairs", "0022_remove_device_blocked_reason"),
    ]

    operations = [
        migrations.CreateModel(
            name="Purchase",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "order_ref",
                    models.CharField(
                        blank=True,
                        help_text="Order number/reference ('13-14739-66407'). Blank for cash/local buys.",
                        max_length=200,
                    ),
                ),
                (
                    "total_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="What the whole lot cost. 0 = own stock; null = unknown.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("purchased_on", models.DateField(blank=True, null=True)),
                (
                    "expected_units",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text=(
                            "Units the lot should yield ('2x DS4' = 2). Used as the unit-price "
                            "divisor while device rows are still being entered; blank = divide by "
                            "actual linked devices."
                        ),
                        null=True,
                    ),
                ),
                (
                    "note",
                    models.TextField(
                        blank=True, help_text="The lot as ordered ('2x DS4 controllers, untested')."
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "source",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="purchases",
                        to="repairs.source",
                    ),
                ),
            ],
            options={"ordering": ["-purchased_on", "-id"]},
        ),
        migrations.AddField(
            model_name="device",
            name="purchase",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="devices",
                to="repairs.purchase",
                help_text=(
                    "The buy event this unit came from — source, order # and money live "
                    "there. Null = found/own-stock without a buy record."
                ),
            ),
        ),
        migrations.RunPython(build_purchases, migrations.RunPython.noop),
        migrations.RemoveField(model_name="device", name="source"),
        migrations.RemoveField(model_name="device", name="acquisition_price"),
    ]

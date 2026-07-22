"""Buy-event behavior — money on the purchase, derived unit price, parts kind."""

from decimal import Decimal

from django.test import TestCase

from repairs.models import Device, Purchase


class PurchaseTests(TestCase):
    """Money lives on the buy event; per-unit price is derived, never stored."""

    def test_create_purchase_resolves_source_and_links_devices(self):
        res = self.client.post(
            "/api/v1/purchases/",
            {
                "source": "eBay",
                "order_ref": "111-1231312",
                "total_price": "20.00",
                "expected_units": 4,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        purchase = Purchase.objects.get(order_ref="111-1231312")
        self.assertEqual(purchase.source.name, "eBay")
        res = self.client.post(
            "/api/v1/inventory/",
            {"purchase": purchase.pk, "status": "shipped"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(purchase.devices.count(), 1)

    def test_unit_price_prefers_expected_units_over_row_count(self):
        purchase = Purchase.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(purchase=purchase)  # only 1 of 4 rows entered so far
        self.assertEqual(purchase.unit_price, Decimal("5.00"))

    def test_unit_price_falls_back_to_linked_device_count(self):
        purchase = Purchase.objects.create(total_price=Decimal("30.00"))
        Device.objects.create(purchase=purchase)
        Device.objects.create(purchase=purchase)
        self.assertEqual(purchase.unit_price, Decimal("15.00"))

    def test_inventory_embeds_purchase_with_unit_price(self):
        purchase = Purchase.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(purchase=purchase, status="shipped")
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertEqual(row["purchase"]["unit_price"], "5.00")
        self.assertEqual(row["purchase"]["total_price"], "20.00")

    def test_parts_purchase_round_trips_kind_and_label(self):
        res = self.client.post(
            "/api/v1/purchases/",
            {
                "kind": "parts",
                "label": "DS4 hall module 20-pack",
                "source": "eBay",
                "total_price": "34.01",
                "expected_units": 20,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        purchase = Purchase.objects.get(label="DS4 hall module 20-pack")
        self.assertEqual(purchase.kind, "parts")
        self.assertEqual(str(purchase), "DS4 hall module 20-pack")
        # And it comes back typed on the list endpoint.
        row = next(
            r for r in self.client.get("/api/v1/purchases/").json() if r["id"] == purchase.pk
        )
        self.assertEqual(row["kind"], "parts")
        # Per-piece price still derives off expected_units.
        self.assertEqual(row["unit_price"], "1.70")

    def test_purchase_kind_defaults_to_device(self):
        res = self.client.post(
            "/api/v1/purchases/",
            {"source": "eBay", "order_ref": "22-00000-00001"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Purchase.objects.get(order_ref="22-00000-00001").kind, "device")

    def test_options_purchases_exclude_parts_kind(self):
        device_lot = Purchase.objects.create(order_ref="27-11111-11111")
        Purchase.objects.create(kind="parts", label="hall modules")
        ids = [p["id"] for p in self.client.get("/api/v1/options/").json()["purchases"]]
        self.assertEqual(ids, [device_lot.pk])

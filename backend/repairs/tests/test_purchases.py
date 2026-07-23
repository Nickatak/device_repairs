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


class MixedLotCostTests(TestCase):
    """cost_override carves explicit money out of the lot; the rest split evenly."""

    def test_override_reprices_the_remainder(self):
        # $100 lot of 5: two DS5s pinned at $30 each → three DS4s split the $40.
        lot = Purchase.objects.create(total_price=Decimal("100.00"), expected_units=5)
        Device.objects.create(purchase=lot, cost_override=Decimal("30.00"))
        Device.objects.create(purchase=lot, cost_override=Decimal("30.00"))
        plain = Device.objects.create(purchase=lot)
        self.assertEqual(lot.unit_price, Decimal("13.33"))
        self.assertEqual(plain.unit_cost, Decimal("13.33"))

    def test_overridden_unit_reports_its_own_cost(self):
        lot = Purchase.objects.create(total_price=Decimal("100.00"), expected_units=5)
        pinned = Device.objects.create(purchase=lot, cost_override=Decimal("30.00"))
        self.assertEqual(pinned.unit_cost, Decimal("30.00"))

    def test_all_units_overridden_leaves_no_default_share(self):
        lot = Purchase.objects.create(total_price=Decimal("60.00"), expected_units=2)
        Device.objects.create(purchase=lot, cost_override=Decimal("40.00"))
        Device.objects.create(purchase=lot, cost_override=Decimal("20.00"))
        self.assertIsNone(lot.unit_price)

    def test_homogeneous_lot_unchanged(self):
        lot = Purchase.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(purchase=lot)
        self.assertEqual(lot.unit_price, Decimal("5.00"))

    def test_cost_override_writable_via_api(self):
        lot = Purchase.objects.create(total_price=Decimal("100.00"), expected_units=2)
        device = Device.objects.create(purchase=lot)
        res = self.client.patch(
            f"/api/v1/inventory/{device.pk}/",
            {"cost_override": "70.00"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(lot.unit_price, Decimal("30.00"))


class PurchaseDetailTests(TestCase):
    """The purchase page payload and the arrival action."""

    def test_detail_embeds_unit_rows(self):
        lot = Purchase.objects.create(total_price=Decimal("30.00"), expected_units=2)
        Device.objects.create(purchase=lot, status="shipped")
        Device.objects.create(purchase=lot, status="shipped", cost_override=Decimal("18.00"))
        data = self.client.get(f"/api/v1/purchases/{lot.pk}/").json()
        self.assertEqual(len(data["devices"]), 2)
        costs = sorted(d["unit_cost"] for d in data["devices"])
        self.assertEqual(costs, ["12.00", "18.00"])

    def test_arrive_stamps_date_and_flips_shipped_units_only(self):
        lot = Purchase.objects.create()
        shipped = Device.objects.create(purchase=lot, status="shipped")
        already_bench = Device.objects.create(purchase=lot, status="in_repair")
        other_lot_unit = Device.objects.create(
            purchase=Purchase.objects.create(), status="shipped"
        )
        res = self.client.post(
            f"/api/v1/purchases/{lot.pk}/arrive/",
            {"date": "2026-07-20"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"arrived_on": "2026-07-20", "units_acquired": 1})
        lot.refresh_from_db()
        shipped.refresh_from_db()
        already_bench.refresh_from_db()
        other_lot_unit.refresh_from_db()
        self.assertEqual(str(lot.arrived_on), "2026-07-20")
        self.assertEqual(shipped.status, "acquired")
        self.assertEqual(already_bench.status, "in_repair")
        self.assertEqual(other_lot_unit.status, "shipped")

    def test_arrive_defaults_to_today(self):
        from django.utils import timezone

        lot = Purchase.objects.create()
        res = self.client.post(
            f"/api/v1/purchases/{lot.pk}/arrive/", {}, content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        lot.refresh_from_db()
        self.assertEqual(lot.arrived_on, timezone.localdate())

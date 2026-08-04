"""Buy-event behavior — money on the order, derived unit price, parts kind."""

from decimal import Decimal

from django.test import TestCase

from repairs.models import Device, Order


class OrderTests(TestCase):
    """Money lives on the buy event; per-unit price is derived, never stored."""

    def test_create_order_resolves_source_and_links_devices(self):
        res = self.client.post(
            "/api/v1/orders/",
            {
                "source": "eBay",
                "order_ref": "111-1231312",
                "total_price": "20.00",
                "expected_units": 4,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        order = Order.objects.get(order_ref="111-1231312")
        self.assertEqual(order.source.name, "eBay")
        res = self.client.post(
            "/api/v1/inventory/",
            {"order": order.pk, "status": "shipped"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(order.devices.count(), 1)

    def test_unit_price_prefers_expected_units_over_row_count(self):
        order = Order.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(order=order)  # only 1 of 4 rows entered so far
        self.assertEqual(order.unit_price, Decimal("5.00"))

    def test_unit_price_falls_back_to_linked_device_count(self):
        order = Order.objects.create(total_price=Decimal("30.00"))
        Device.objects.create(order=order)
        Device.objects.create(order=order)
        self.assertEqual(order.unit_price, Decimal("15.00"))

    def test_inventory_embeds_order_with_unit_price(self):
        order = Order.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(order=order, status="shipped")
        row = self.client.get("/api/v1/inventory/").json()[0]
        self.assertEqual(row["order"]["unit_price"], "5.00")
        self.assertEqual(row["order"]["total_price"], "20.00")

    def test_parts_order_round_trips_kind_and_label(self):
        res = self.client.post(
            "/api/v1/orders/",
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
        order = Order.objects.get(label="DS4 hall module 20-pack")
        self.assertEqual(order.kind, "parts")
        self.assertEqual(str(order), "DS4 hall module 20-pack")
        # And it comes back typed on the list endpoint.
        row = next(
            r for r in self.client.get("/api/v1/orders/").json() if r["id"] == order.pk
        )
        self.assertEqual(row["kind"], "parts")
        # Per-piece price still derives off expected_units.
        self.assertEqual(row["unit_price"], "1.70")

    def test_order_kind_defaults_to_device(self):
        res = self.client.post(
            "/api/v1/orders/",
            {"source": "eBay", "order_ref": "22-00000-00001"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Order.objects.get(order_ref="22-00000-00001").kind, "device")

    def test_options_orders_exclude_parts_kind(self):
        device_lot = Order.objects.create(order_ref="27-11111-11111")
        Order.objects.create(kind="parts", label="hall modules")
        ids = [p["id"] for p in self.client.get("/api/v1/options/").json()["orders"]]
        self.assertEqual(ids, [device_lot.pk])


class MixedLotCostTests(TestCase):
    """cost_override carves explicit money out of the lot; the rest split evenly."""

    def test_override_reprices_the_remainder(self):
        # $100 lot of 5: two DS5s pinned at $30 each → three DS4s split the $40.
        lot = Order.objects.create(total_price=Decimal("100.00"), expected_units=5)
        Device.objects.create(order=lot, cost_override=Decimal("30.00"))
        Device.objects.create(order=lot, cost_override=Decimal("30.00"))
        plain = Device.objects.create(order=lot)
        self.assertEqual(lot.unit_price, Decimal("13.33"))
        self.assertEqual(plain.unit_cost, Decimal("13.33"))

    def test_overridden_unit_reports_its_own_cost(self):
        lot = Order.objects.create(total_price=Decimal("100.00"), expected_units=5)
        pinned = Device.objects.create(order=lot, cost_override=Decimal("30.00"))
        self.assertEqual(pinned.unit_cost, Decimal("30.00"))

    def test_all_units_overridden_leaves_no_default_share(self):
        lot = Order.objects.create(total_price=Decimal("60.00"), expected_units=2)
        Device.objects.create(order=lot, cost_override=Decimal("40.00"))
        Device.objects.create(order=lot, cost_override=Decimal("20.00"))
        self.assertIsNone(lot.unit_price)

    def test_homogeneous_lot_unchanged(self):
        lot = Order.objects.create(total_price=Decimal("20.00"), expected_units=4)
        Device.objects.create(order=lot)
        self.assertEqual(lot.unit_price, Decimal("5.00"))

    def test_cost_override_writable_via_api(self):
        lot = Order.objects.create(total_price=Decimal("100.00"), expected_units=2)
        device = Device.objects.create(order=lot)
        res = self.client.patch(
            f"/api/v1/inventory/{device.pk}/",
            {"cost_override": "70.00"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(lot.unit_price, Decimal("30.00"))


class OrderDetailTests(TestCase):
    """The order page payload and the arrival action."""

    def test_detail_embeds_unit_rows(self):
        lot = Order.objects.create(total_price=Decimal("30.00"), expected_units=2)
        Device.objects.create(order=lot, status="shipped")
        Device.objects.create(order=lot, status="shipped", cost_override=Decimal("18.00"))
        data = self.client.get(f"/api/v1/orders/{lot.pk}/").json()
        self.assertEqual(len(data["devices"]), 2)
        costs = sorted(d["unit_cost"] for d in data["devices"])
        self.assertEqual(costs, ["12.00", "18.00"])

    def test_arrive_stamps_date_and_flips_shipped_units_only(self):
        lot = Order.objects.create()
        shipped = Device.objects.create(order=lot, status="shipped")
        already_bench = Device.objects.create(order=lot, status="disassembled_diagnosing")
        other_lot_unit = Device.objects.create(
            order=Order.objects.create(), status="shipped"
        )
        res = self.client.post(
            f"/api/v1/orders/{lot.pk}/arrive/",
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
        self.assertEqual(already_bench.status, "disassembled_diagnosing")
        self.assertEqual(other_lot_unit.status, "shipped")

    def test_arrive_defaults_to_today(self):
        from django.utils import timezone

        lot = Order.objects.create()
        res = self.client.post(
            f"/api/v1/orders/{lot.pk}/arrive/", {}, content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        lot.refresh_from_db()
        self.assertEqual(lot.arrived_on, timezone.localdate())

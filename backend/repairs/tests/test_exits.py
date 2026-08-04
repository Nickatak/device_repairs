"""Exit behavior — the departure event, its status-flip rule, and the cash rollup."""

from decimal import Decimal

from django.test import TestCase

from repairs.models import Device, Exit, Order


class ExitTests(TestCase):
    """An exit is an event row; recording one flips the device to exited."""

    def test_create_exit_flips_device_status(self):
        device = Device.objects.create(status="awaiting_exit")
        res = self.client.post(
            "/api/v1/exits/",
            {
                "device": device.pk,
                "kind": "sold",
                "happened_on": "2026-07-22",
                "sale_price": "34.99",
                "fees": "8.12",
                "to_who": "buyer_handle",
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        device.refresh_from_db()
        self.assertEqual(device.status, "exited")
        exit_row = device.exits.get()
        self.assertEqual(exit_row.net, Decimal("26.87"))

    def test_return_then_resell_is_two_events(self):
        device = Device.objects.create(status="awaiting_exit")
        first = Exit.objects.create(device=device, kind="sold", sale_price=Decimal("30"))
        second = Exit.objects.create(
            device=device, kind="returned", sale_price=Decimal("-30")
        )
        self.assertEqual(device.exits.count(), 2)
        self.assertNotEqual(first.pk, second.pk)

    def test_net_is_null_without_sale_money(self):
        device = Device.objects.create()
        gift = Exit.objects.create(device=device, kind="gifted")
        self.assertIsNone(gift.net)

    def test_patch_exit_corrects_money(self):
        device = Device.objects.create()
        exit_row = Exit.objects.create(device=device, kind="sold", sale_price=Decimal("30"))
        res = self.client.patch(
            f"/api/v1/exits/{exit_row.pk}/",
            {"fees": "5.00"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        exit_row.refresh_from_db()
        self.assertEqual(exit_row.net, Decimal("25.00"))

    def test_device_detail_embeds_exits(self):
        device = Device.objects.create()
        Exit.objects.create(
            device=device, kind="sold", sale_price=Decimal("42.87"), happened_on="2026-07-19"
        )
        payload = self.client.get(f"/api/v1/inventory/{device.pk}/").json()
        self.assertEqual(len(payload["exits"]), 1)
        self.assertEqual(payload["exits"][0]["kind"], "sold")
        self.assertEqual(payload["exits"][0]["net"], "42.87")

    def test_options_people_pool_includes_exit_counterparties(self):
        Order.objects.create(from_who="seller_a")
        Exit.objects.create(device=Device.objects.create(), kind="sold", to_who="buyer_b")
        people = self.client.get("/api/v1/options/").json()["people"]
        self.assertIn("seller_a", people)
        self.assertIn("buyer_b", people)


class CashSummaryTests(TestCase):
    """Money out = all orders; money in = exit sale money net of fees."""

    def test_rollup_math(self):
        Order.objects.create(total_price=Decimal("100.00"))
        Order.objects.create(kind="parts", total_price=Decimal("25.50"))
        d1, d2 = Device.objects.create(), Device.objects.create()
        Exit.objects.create(device=d1, kind="sold", sale_price=Decimal("60.00"), fees=Decimal("10.00"))
        Exit.objects.create(device=d2, kind="gifted")  # no money — must not crash the sums

        data = self.client.get("/api/v1/cash/").json()
        self.assertEqual(data["money_out"], "125.50")
        self.assertEqual(data["money_in"], "50.00")
        self.assertEqual(data["net"], "-75.50")

    def test_returned_refund_counts_as_money_in(self):
        Order.objects.create(total_price=Decimal("40.00"))
        device = Device.objects.create()
        Exit.objects.create(device=device, kind="returned", sale_price=Decimal("40.00"))
        data = self.client.get("/api/v1/cash/").json()
        self.assertEqual(data["money_in"], "40.00")
        self.assertEqual(data["net"], "0.00")

"""Cash position — the reconcile.py readout that froze with the CSVs.

Money out = every order (device lots AND parts orders). Money in = exit
sale money net of fees; a returned kind's refund arrives via sale_price the
same way. Parts installed into devices are already order rows, so nothing
double-counts.
"""

from decimal import Decimal

from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from repairs.models import Exit, Order


class CashSummaryView(APIView):
    """GET = money out / money in / net position, whole-project scope."""

    def get(self, request):
        money_out = Order.objects.aggregate(total=Sum("total_price"))["total"] or Decimal("0")
        sales = Exit.objects.aggregate(total=Sum("sale_price"))["total"] or Decimal("0")
        fees = Exit.objects.aggregate(total=Sum("fees"))["total"] or Decimal("0")
        money_in = sales - fees
        return Response(
            {
                "money_out": str(money_out),
                "money_in": str(money_in),
                "net": str(money_in - money_out),
                "order_count": Order.objects.count(),
                "exit_count": Exit.objects.count(),
            }
        )

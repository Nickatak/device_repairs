"""Order endpoints — the buy-event list, detail (with linked units), and arrival."""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from repairs.models import Device, Order
from repairs.serializers import (
    OrderDetailSerializer,
    OrderSerializer,
    OrderWriteSerializer,
)


class OrderListCreateView(ListCreateAPIView):
    """GET = buy events newest-first; POST = record a new order."""

    queryset = Order.objects.select_related("source").prefetch_related("devices")

    def get_serializer_class(self):
        return (
            OrderWriteSerializer
            if self.request.method == "POST"
            else OrderSerializer
        )


class OrderDetailView(RetrieveUpdateAPIView):
    """GET a order with its linked device rows; PATCH its own fields."""

    queryset = Order.objects.select_related("source").prefetch_related(
        "devices__location", "devices__reference", "devices__repairs"
    )

    def get_serializer_class(self):
        return (
            OrderWriteSerializer
            if self.request.method in ("PUT", "PATCH")
            else OrderDetailSerializer
        )


class OrderArriveView(APIView):
    """POST = the lot physically landed: stamp arrived_on and flip the lot's
    shipped units to acquired in one stroke (the ledger's on-arrival rule).
    Optional body {"date": "YYYY-MM-DD"} backdates; default is today.
    Units already past shipped are left alone."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        order.arrived_on = request.data.get("date") or timezone.localdate()
        order.save(update_fields=["arrived_on"])
        # Queryset update bypasses save(), so stamp touched_at explicitly —
        # the arrival flip is an edit like any other.
        flipped = order.devices.filter(status=Device.Status.SHIPPED).update(
            status=Device.Status.ACQUIRED, touched_at=timezone.now()
        )
        return Response({"arrived_on": str(order.arrived_on), "units_acquired": flipped})

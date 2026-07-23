"""Purchase endpoints — the buy-event list, detail (with linked units), and arrival."""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from repairs.models import Device, Purchase
from repairs.serializers import (
    PurchaseDetailSerializer,
    PurchaseSerializer,
    PurchaseWriteSerializer,
)


class PurchaseListCreateView(ListCreateAPIView):
    """GET = buy events newest-first; POST = record a new purchase."""

    queryset = Purchase.objects.select_related("source").prefetch_related("devices")

    def get_serializer_class(self):
        return (
            PurchaseWriteSerializer
            if self.request.method == "POST"
            else PurchaseSerializer
        )


class PurchaseDetailView(RetrieveUpdateAPIView):
    """GET a purchase with its linked device rows; PATCH its own fields."""

    queryset = Purchase.objects.select_related("source").prefetch_related(
        "devices__location", "devices__reference", "devices__repairs"
    )

    def get_serializer_class(self):
        return (
            PurchaseWriteSerializer
            if self.request.method in ("PUT", "PATCH")
            else PurchaseDetailSerializer
        )


class PurchaseArriveView(APIView):
    """POST = the lot physically landed: stamp arrived_on and flip the lot's
    shipped units to acquired in one stroke (the ledger's on-arrival rule).
    Optional body {"date": "YYYY-MM-DD"} backdates; default is today.
    Units already past shipped are left alone."""

    def post(self, request, pk):
        purchase = get_object_or_404(Purchase, pk=pk)
        purchase.arrived_on = request.data.get("date") or timezone.localdate()
        purchase.save(update_fields=["arrived_on"])
        flipped = purchase.devices.filter(status=Device.Status.SHIPPED).update(
            status=Device.Status.ACQUIRED
        )
        return Response({"arrived_on": str(purchase.arrived_on), "units_acquired": flipped})

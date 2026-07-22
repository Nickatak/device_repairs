"""Purchase endpoints — the buy-event list and edit paths."""

from rest_framework.generics import ListCreateAPIView, UpdateAPIView

from repairs.models import Purchase
from repairs.serializers import PurchaseSerializer, PurchaseWriteSerializer


class PurchaseListCreateView(ListCreateAPIView):
    """GET = buy events newest-first; POST = record a new purchase."""

    queryset = Purchase.objects.select_related("source").prefetch_related("devices")

    def get_serializer_class(self):
        return (
            PurchaseWriteSerializer
            if self.request.method == "POST"
            else PurchaseSerializer
        )


class PurchaseUpdateView(UpdateAPIView):
    """PATCH a purchase (typo fixes, expected-units corrections). No delete path."""

    serializer_class = PurchaseWriteSerializer
    queryset = Purchase.objects.all()

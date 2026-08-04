"""Stock endpoints — bucket list/detail, intakes, and the recount stroke.

No delete paths, house style. The count is never PATCHed directly: it moves
via intakes (+), bench Part draws (−), and POST recount (override + stamp).
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, CreateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from repairs.models import StockIntake, StockItem
from repairs.serializers import (
    RecountSerializer,
    StockIntakeWriteSerializer,
    StockItemSerializer,
    StockItemWriteSerializer,
)

STOCK_QUERYSET = StockItem.objects.prefetch_related(
    "fits_references",
    "fits_revisions__reference",
    "intakes__order__source",
    "draws",
)


class StockListCreateView(ListCreateAPIView):
    """GET = every bucket with live counts; POST = mint a new SKU."""

    queryset = STOCK_QUERYSET

    def get_serializer_class(self):
        return (
            StockItemWriteSerializer
            if self.request.method == "POST"
            else StockItemSerializer
        )


class StockDetailView(RetrieveUpdateAPIView):
    """GET a bucket; PATCH its identity fields (never the count)."""

    queryset = STOCK_QUERYSET

    def get_serializer_class(self):
        return (
            StockItemWriteSerializer
            if self.request.method in ("PUT", "PATCH")
            else StockItemSerializer
        )


class StockRecountView(APIView):
    """POST {"count": N} — the physical recount: new base, fresh stamp.
    Also the way a bucket's counting LIFE starts (first recount sets the base
    that intakes/draws move from)."""

    def post(self, request, pk):
        item = get_object_or_404(StockItem, pk=pk)
        serializer = RecountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.last_count = serializer.validated_data["count"]
        item.counted_at = timezone.now()
        item.save(update_fields=["last_count", "counted_at"])
        return Response(
            {"last_count": item.last_count, "counted_at": item.counted_at.isoformat()}
        )


class StockIntakeCreateView(CreateAPIView):
    """POST units entering a bucket from a parts order."""

    serializer_class = StockIntakeWriteSerializer
    queryset = StockIntake.objects.all()


class StockIntakeUpdateView(UpdateAPIView):
    """PATCH an intake (quantity corrections). Derived counts self-heal."""

    serializer_class = StockIntakeWriteSerializer
    queryset = StockIntake.objects.all()

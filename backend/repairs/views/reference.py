"""Price-sheet endpoints — the catalog list and lane policies. Read-only."""

from rest_framework.generics import ListAPIView

from repairs.models import DeviceReference, Lane
from repairs.serializers import DeviceReferenceSerializer, LaneSerializer


class ReferenceListView(ListAPIView):
    """GET = the full catalog + price sheet. Search/filter is done client-side."""

    serializer_class = DeviceReferenceSerializer
    queryset = DeviceReference.objects.select_related("lane").prefetch_related(
        "comp_pulls", "issues"
    )


class LaneListView(ListAPIView):
    """GET = lanes with their policy prose, for the reference page's lane panel."""

    serializer_class = LaneSerializer
    queryset = Lane.objects.all()

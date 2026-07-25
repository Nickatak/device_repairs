"""Price-sheet endpoints — the catalog list and lane policies. Read-only,
except revisions (see serializers.reference for the rationale)."""

from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView

from repairs.models import DeviceReference, Lane, Revision
from repairs.serializers import (
    DeviceReferenceSerializer,
    LaneSerializer,
    RevisionWriteSerializer,
)


class ReferenceListView(ListAPIView):
    """GET = the full catalog + price sheet. Search/filter is done client-side."""

    serializer_class = DeviceReferenceSerializer
    queryset = DeviceReference.objects.select_related("lane").prefetch_related(
        "comp_pulls__variant", "issues", "variants", "revisions"
    )


class LaneListView(ListAPIView):
    """GET = lanes with their policy prose, for the reference page's lane panel."""

    serializer_class = LaneSerializer
    queryset = Lane.objects.all()


class RevisionCreateView(CreateAPIView):
    """POST a new board revision onto a catalog row. No delete path by design."""

    serializer_class = RevisionWriteSerializer
    queryset = Revision.objects.all()


class RevisionUpdateView(UpdateAPIView):
    """PATCH a revision — accrete bench knowledge into `note`. No delete path by design."""

    serializer_class = RevisionWriteSerializer
    queryset = Revision.objects.all()

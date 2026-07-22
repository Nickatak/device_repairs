"""Public read API views.

No auth in the MVP (single user, local). DRF's default permission with no
DEFAULT_PERMISSION_CLASSES set is AllowAny, so these are open reads.
"""

from django.db.models import F, Max
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Device,
    DeviceReference,
    Lane,
    Location,
    Measurement,
    Note,
    Purchase,
    Repair,
    Source,
)
from .serializers import (
    DeviceBulkCreateSerializer,
    DeviceDetailSerializer,
    DeviceReferenceSerializer,
    DeviceWriteSerializer,
    InventoryDeviceSerializer,
    LaneSerializer,
    MeasurementWriteSerializer,
    NoteWriteSerializer,
    PurchaseSerializer,
    PurchaseWriteSerializer,
    RepairCreateSerializer,
    RepairWriteSerializer,
)


class InventoryListView(ListCreateAPIView):
    """GET = all devices on hand with current status; POST = create a device."""

    queryset = (
        Device.objects.select_related("purchase__source", "location", "reference")
        .prefetch_related("repairs")
        .order_by("reference__brand", "reference__name", "id")
    )

    def get_serializer_class(self):
        return (
            DeviceWriteSerializer
            if self.request.method == "POST"
            else InventoryDeviceSerializer
        )


class DeviceDetailView(RetrieveUpdateAPIView):
    """GET a single device with its repairs + steps; PATCH its own fields."""

    queryset = Device.objects.select_related(
        "purchase__source", "location", "reference", "reference__lane"
    ).prefetch_related(
        "repairs__notes__measurements",
        "repairs__notes__subnotes__measurements",
    )

    def get_serializer_class(self):
        return (
            DeviceWriteSerializer
            if self.request.method in ("PUT", "PATCH")
            else DeviceDetailSerializer
        )


class ReferenceListView(ListAPIView):
    """GET = the full catalog + price sheet. Search/filter is done client-side."""

    serializer_class = DeviceReferenceSerializer
    queryset = DeviceReference.objects.select_related("lane").prefetch_related("comp_pulls")


class LaneListView(ListAPIView):
    """GET = lanes with their policy prose, for the reference page's lane panel."""

    serializer_class = LaneSerializer
    queryset = Lane.objects.all()


class RepairCreateView(CreateAPIView):
    """POST a new repair — bench work started on a device. Never a status carrier."""

    serializer_class = RepairCreateSerializer
    queryset = Repair.objects.all()


class RepairUpdateView(UpdateAPIView):
    """PATCH a repair's phase track / notes. No delete path by design."""

    serializer_class = RepairWriteSerializer
    queryset = Repair.objects.all()


class NoteCreateView(CreateAPIView):
    """POST a new note (attached to a repair). No delete path by design."""

    serializer_class = NoteWriteSerializer
    queryset = Note.objects.all()


class NoteUpdateView(UpdateAPIView):
    """PATCH an existing note. No delete path by design."""

    serializer_class = NoteWriteSerializer
    queryset = Note.objects.all()


class MeasurementCreateView(CreateAPIView):
    """POST a new measurement (attached to a step). No delete path by design."""

    serializer_class = MeasurementWriteSerializer
    queryset = Measurement.objects.all()


class MeasurementUpdateView(UpdateAPIView):
    """PATCH an existing measurement. No delete path by design."""

    serializer_class = MeasurementWriteSerializer
    queryset = Measurement.objects.all()


class DeviceBulkCreateView(APIView):
    """POST N identical device skeletons from one purchase (bulk add)."""

    def post(self, request):
        serializer = DeviceBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        devices = serializer.save()
        return Response(
            {"created": len(devices), "ids": [d.pk for d in devices]}, status=201
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


class PurchaseUpdateView(UpdateAPIView):
    """PATCH a purchase (typo fixes, expected-units corrections). No delete path."""

    serializer_class = PurchaseWriteSerializer
    queryset = Purchase.objects.all()


class OptionsView(APIView):
    """Existing lookup values, for combo-box datalists in the create/edit modal."""

    def get(self, request):
        return Response(
            {
                # Catalog rows for the device form's reference combobox — light
                # projection; the full price-sheet payload stays on /reference/.
                # Most-recently-USED first (highest linked device id — devices
                # carry no timestamp, so row id is the recency proxy); never-used
                # rows follow alphabetically.
                "references": list(
                    DeviceReference.objects.annotate(last_used=Max("units__id"))
                    .order_by(F("last_used").desc(nulls_last=True), "brand", "name")
                    .values("id", "brand", "name", "sku_prefix", "model_numbers")
                ),
                # Most-recently-used first (same device-id proxy as references).
                "locations": list(
                    Location.objects.annotate(last_used=Max("devices__id"))
                    .order_by(F("last_used").desc(nulls_last=True), "name")
                    .values_list("name", flat=True)
                ),
                "sources": list(Source.objects.values_list("name", flat=True)),
                # Shared counterparty pool: everyone seen in purchases' from_who
                # or exits' to_who feeds both comboboxes.
                "people": sorted(
                    set(
                        Purchase.objects.exclude(from_who="").values_list(
                            "from_who", flat=True
                        )
                    )
                    | set(
                        Device.objects.exclude(to_who="").values_list("to_who", flat=True)
                    )
                ),
                # Buy events for the device form's purchase combobox, most
                # recently placed first — device lots only; parts purchases
                # never hold devices. Explicit nulls_last: Postgres would
                # otherwise lead a DESC sort with the undated own-stock rows.
                "purchases": PurchaseSerializer(
                    Purchase.objects.filter(kind=Purchase.Kind.DEVICE)
                    .select_related("source")
                    .prefetch_related("devices")
                    .order_by(F("purchased_on").desc(nulls_last=True), "-id"),
                    many=True,
                ).data,
                "statuses": [
                    {"value": value, "label": label}
                    for value, label in Device.Status.choices
                ],
            }
        )

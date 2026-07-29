"""Inventory endpoints — device list/create, device detail, device notes, bulk add."""

from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from repairs.models import Device, DeviceNote
from repairs.serializers import (
    DeviceBulkCreateSerializer,
    DeviceDetailSerializer,
    DeviceNoteWriteSerializer,
    DeviceWriteSerializer,
    InventoryDeviceSerializer,
)


class InventoryListView(ListCreateAPIView):
    """GET = all devices on hand with current status; POST = create a device."""

    queryset = (
        Device.objects.select_related("purchase__source", "location", "reference")
        .prefetch_related("repairs", "device_notes")
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
        "device_notes__media",
        "reference__issues",
        "reference__variants",
        "reference__comp_pulls__variant",
    )

    def get_serializer_class(self):
        return (
            DeviceWriteSerializer
            if self.request.method in ("PUT", "PATCH")
            else DeviceDetailSerializer
        )


class DeviceNoteCreateView(CreateAPIView):
    """POST a new device-note chunk (unit-grain fact)."""

    serializer_class = DeviceNoteWriteSerializer
    queryset = DeviceNote.objects.all()


class DeviceNoteUpdateView(RetrieveUpdateDestroyAPIView):
    """PATCH / DELETE an existing device-note chunk.

    Deletable since 2026-07-29 (Nick's prune call) — the second deliberate
    exception to the no-delete rule after templates: chunks are a working
    surface that accumulates jam, not the repair log. Guard: a chunk carrying
    photos refuses deletion (media would cascade) — strip or reparent first.
    """

    serializer_class = DeviceNoteWriteSerializer
    queryset = DeviceNote.objects.all()

    def perform_destroy(self, instance):
        if instance.media.exists():
            raise ValidationError(
                "Chunk carries photos — reparent or re-caption them first; media never deletes silently."
            )
        device_id = instance.device_id
        instance.delete()
        Device.touch(device_id)


class DeviceBulkCreateView(APIView):
    """POST N identical device skeletons from one purchase (bulk add)."""

    def post(self, request):
        serializer = DeviceBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        devices = serializer.save()
        return Response(
            {"created": len(devices), "ids": [d.pk for d in devices]}, status=201
        )

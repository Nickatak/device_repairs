"""Bench-work endpoints — repair, note, and measurement create/update. No delete paths by design."""

from rest_framework.generics import CreateAPIView, UpdateAPIView

from repairs.models import Measurement, Note, Repair
from repairs.serializers import (
    MeasurementWriteSerializer,
    NoteWriteSerializer,
    RepairCreateSerializer,
    RepairWriteSerializer,
)


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

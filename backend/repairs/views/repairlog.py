"""Bench-work endpoints — repair, note, measurement, and media create/update. No delete paths by design."""

from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.parsers import FormParser, MultiPartParser

from repairs.models import Measurement, Media, Note, Repair
from repairs.serializers import (
    MeasurementWriteSerializer,
    MediaWriteSerializer,
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


class MediaCreateView(CreateAPIView):
    """POST a photo (multipart: image + caption + note XOR repair). GPS is
    stripped and taken_at extracted server-side. No delete path by design."""

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = MediaWriteSerializer
    queryset = Media.objects.all()


class MediaUpdateView(UpdateAPIView):
    """PATCH caption / reparent an existing photo. The image file is immutable."""

    serializer_class = MediaWriteSerializer
    queryset = Media.objects.all()


class MeasurementCreateView(CreateAPIView):
    """POST a new measurement (attached to a step). No delete path by design."""

    serializer_class = MeasurementWriteSerializer
    queryset = Measurement.objects.all()


class MeasurementUpdateView(UpdateAPIView):
    """PATCH an existing measurement. No delete path by design."""

    serializer_class = MeasurementWriteSerializer
    queryset = Measurement.objects.all()

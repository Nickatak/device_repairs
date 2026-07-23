"""Exit endpoints — record and correct departure events. No delete path by design."""

from rest_framework.generics import CreateAPIView, UpdateAPIView

from repairs.models import Exit
from repairs.serializers import ExitWriteSerializer


class ExitCreateView(CreateAPIView):
    """POST a departure event — also flips the device to exited (serializer rule)."""

    serializer_class = ExitWriteSerializer
    queryset = Exit.objects.all()


class ExitUpdateView(UpdateAPIView):
    """PATCH an exit (money corrections, date fixes). No delete path by design."""

    serializer_class = ExitWriteSerializer
    queryset = Exit.objects.all()

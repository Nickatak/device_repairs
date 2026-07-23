"""Exit payloads — the departure event, read and write paths."""

from rest_framework import serializers

from repairs.models import Device, Exit


class ExitSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    net = serializers.SerializerMethodField()

    class Meta:
        model = Exit
        fields = [
            "id",
            "kind",
            "kind_display",
            "happened_on",
            "sale_price",
            "fees",
            "net",
            "to_who",
            "note",
        ]

    def get_net(self, obj) -> str | None:
        net = obj.net
        return str(net) if net is not None else None


class ExitWriteSerializer(serializers.ModelSerializer):
    """Create / edit an exit. Creating one flips the device to exited —
    the ledger rule: a unit exit = status flip AND an exits row."""

    class Meta:
        model = Exit
        fields = ["id", "device", "kind", "happened_on", "sale_price", "fees", "to_who", "note"]

    def create(self, validated_data):
        exit_row = super().create(validated_data)
        device = exit_row.device
        if device.status != Device.Status.EXITED:
            device.status = Device.Status.EXITED
            device.save(update_fields=["status"])
        return exit_row

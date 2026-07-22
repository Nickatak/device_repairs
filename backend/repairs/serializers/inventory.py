"""Device payloads — inventory list, device detail, write paths for the modals."""

from rest_framework import serializers

from repairs.models import Device, DeviceReference, Location, Purchase

from .purchases import PurchaseSerializer
from .reference import DeviceReferenceSerializer
from .repairlog import RepairWithNotesSerializer


class InventoryDeviceSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    location = serializers.StringRelatedField()
    purchase = PurchaseSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    repair_count = serializers.IntegerField(source="repairs.count", read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "label",
            "ledger_ref",
            "reference",
            "serial",
            "location",
            "purchase",
            "to_who",
            "notes",
            "status",
            "status_display",
            "repair_count",
        ]

    def get_label(self, obj) -> str:
        return str(obj)


class DeviceDetailSerializer(serializers.ModelSerializer):
    """Single device with its repairs and their steps — the device-page payload."""

    label = serializers.SerializerMethodField()
    location = serializers.StringRelatedField()
    purchase = PurchaseSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reference = DeviceReferenceSerializer(read_only=True)
    repairs = RepairWithNotesSerializer(many=True, read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "label",
            "ledger_ref",
            "serial",
            "location",
            "purchase",
            "to_who",
            "notes",
            "status",
            "status_display",
            "reference",
            "repairs",
        ]

    def get_label(self, obj) -> str:
        return str(obj)


class DeviceWriteSerializer(serializers.ModelSerializer):
    """Write path for the create + edit modals — Device's own fields only.

    Identity is the `reference` FK into the catalog (picked via combobox; null =
    off-catalog unit). Money/source come via the `purchase` FK — the buy event —
    never as device-local fields. `status` is the device's own lifecycle field —
    writing it never touches repairs (the old phantom-repair-as-status-carrier
    behavior is gone).
    """

    # Lookup fields → which model resolves them.
    LOOKUPS = {"location": Location}

    reference = serializers.PrimaryKeyRelatedField(
        queryset=DeviceReference.objects.all(), required=False, allow_null=True
    )
    purchase = serializers.PrimaryKeyRelatedField(
        queryset=Purchase.objects.all(), required=False, allow_null=True
    )
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Device
        fields = [
            "reference",
            "serial",
            "location",
            "purchase",
            "to_who",
            "notes",
            "status",
        ]

    def _resolve_lookups(self, validated_data):
        """Pop each provided lookup field, returning {field: instance-or-None}."""
        resolved = {}
        for field, model_cls in self.LOOKUPS.items():
            if field in validated_data:
                name = (validated_data.pop(field) or "").strip()
                resolved[field] = model_cls.objects.get_or_create(name=name)[0] if name else None
        return resolved

    def create(self, validated_data):
        resolved = self._resolve_lookups(validated_data)
        return Device.objects.create(**validated_data, **resolved)

    def update(self, instance, validated_data):
        for field, obj in self._resolve_lookups(validated_data).items():
            setattr(instance, field, obj)
        return super().update(instance, validated_data)


class DeviceBulkCreateSerializer(serializers.Serializer):
    """Spawn N identical device rows from one purchase ('3x controllers arrived').

    Per-unit identity (model #, serial) is refined afterward on each row — this
    creates the skeletons that the lot's money splits across.
    """

    purchase = serializers.PrimaryKeyRelatedField(
        queryset=Purchase.objects.all(), required=False, allow_null=True, default=None
    )
    reference = serializers.PrimaryKeyRelatedField(
        queryset=DeviceReference.objects.all(), required=False, allow_null=True, default=None
    )
    location = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=Device.Status.choices, default=Device.Status.SHIPPED)
    quantity = serializers.IntegerField(min_value=1, max_value=100)

    def create(self, validated_data):
        name = validated_data["location"].strip()
        location = Location.objects.get_or_create(name=name)[0] if name else None
        return [
            Device.objects.create(
                purchase=validated_data["purchase"],
                reference=validated_data["reference"],
                location=location,
                notes=validated_data["notes"],
                status=validated_data["status"],
            )
            for _ in range(validated_data["quantity"])
        ]

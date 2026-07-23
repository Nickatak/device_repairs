"""Device payloads — inventory list, device detail, write paths for the modals."""

from rest_framework import serializers

from repairs.models import Device, DeviceReference, Location, Purchase

from .exits import ExitSerializer
from .purchases import PurchaseSerializer
from .reference import DeviceReferenceSerializer
from .repairlog import RepairWithNotesSerializer


class InventoryDeviceSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    location = serializers.StringRelatedField()
    purchase = PurchaseSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    repair_count = serializers.IntegerField(source="repairs.count", read_only=True)
    unit_cost = serializers.SerializerMethodField()

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
            "notes",
            "status",
            "status_display",
            "repair_count",
            "cost_override",
            "unit_cost",
        ]

    def get_label(self, obj) -> str:
        return str(obj)

    def get_unit_cost(self, obj) -> str | None:
        cost = obj.unit_cost
        return str(cost) if cost is not None else None


class DeviceDetailSerializer(serializers.ModelSerializer):
    """Single device with its repairs and their steps — the device-page payload."""

    label = serializers.SerializerMethodField()
    location = serializers.StringRelatedField()
    purchase = PurchaseSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reference = DeviceReferenceSerializer(read_only=True)
    repairs = RepairWithNotesSerializer(many=True, read_only=True)
    exits = ExitSerializer(many=True, read_only=True)
    unit_cost = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id",
            "label",
            "ledger_ref",
            "serial",
            "location",
            "purchase",
            "notes",
            "status",
            "status_display",
            "reference",
            "repairs",
            "exits",
            "cost_override",
            "unit_cost",
        ]

    def get_label(self, obj) -> str:
        return str(obj)

    def get_unit_cost(self, obj) -> str | None:
        cost = obj.unit_cost
        return str(cost) if cost is not None else None


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
            "notes",
            "status",
            "cost_override",
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


class BulkLineSerializer(serializers.Serializer):
    """One homogeneous slice of a lot: N units of one catalog model."""

    reference = serializers.PrimaryKeyRelatedField(
        queryset=DeviceReference.objects.all(), required=False, allow_null=True, default=None
    )
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class DeviceBulkCreateSerializer(serializers.Serializer):
    """Spawn device rows from one purchase ('2x DS5 + 3x DS4 arrived').

    Lines carry the heterogeneity — each line is reference × quantity; shared
    fields (purchase, location, status, notes) apply to every spawned row.
    Per-unit identity (serial, cost override) is refined afterward on each row.
    """

    purchase = serializers.PrimaryKeyRelatedField(
        queryset=Purchase.objects.all(), required=False, allow_null=True, default=None
    )
    location = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=Device.Status.choices, default=Device.Status.SHIPPED)
    lines = BulkLineSerializer(many=True, allow_empty=False)

    def validate_lines(self, lines):
        if sum(line["quantity"] for line in lines) > 100:
            raise serializers.ValidationError("At most 100 units per bulk add.")
        return lines

    def create(self, validated_data):
        name = validated_data["location"].strip()
        location = Location.objects.get_or_create(name=name)[0] if name else None
        return [
            Device.objects.create(
                purchase=validated_data["purchase"],
                reference=line["reference"],
                location=location,
                notes=validated_data["notes"],
                status=validated_data["status"],
            )
            for line in validated_data["lines"]
            for _ in range(line["quantity"])
        ]

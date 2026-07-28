"""Device payloads — inventory list, device detail, write paths for the modals."""

from rest_framework import serializers

from repairs.models import Device, DeviceNote, DeviceReference, Location, Purchase, Revision

from .reference import RevisionSerializer

from .exits import ExitSerializer
from .purchases import PurchaseSerializer
from .reference import DeviceReferenceSerializer
from .repairlog import MediaSerializer, RepairWithNotesSerializer


class DeviceNoteSerializer(serializers.ModelSerializer):
    """A unit-fact chunk with its photos — nested in the device payloads."""

    media = MediaSerializer(many=True, read_only=True)

    class Meta:
        model = DeviceNote
        fields = ["id", "position", "title", "text", "created_at", "media"]


class DeviceNoteWriteSerializer(serializers.ModelSerializer):
    """Create / edit a device-note chunk. No delete path, same as the repair log."""

    class Meta:
        model = DeviceNote
        fields = ["id", "device", "position", "title", "text"]


class InventoryDeviceSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    location = serializers.StringRelatedField()
    purchase = PurchaseSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    repair_count = serializers.IntegerField(source="repairs.count", read_only=True)
    unit_cost = serializers.SerializerMethodField()
    revision = RevisionSerializer(read_only=True)
    notes = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id",
            "label",
            "ledger_ref",
            "reference",
            "revision",
            "serial",
            "location",
            "purchase",
            "notes",
            "status",
            "status_display",
            "repair_count",
            "cost_override",
            "unit_cost",
            "touched_at",
        ]

    def get_label(self, obj) -> str:
        return str(obj)

    def get_notes(self, obj) -> str:
        """Chunks flattened to one string — the list payload's search/display shape."""
        return "\n\n".join(
            f"{n.title}\n{n.text}" if n.title else n.text
            for n in obj.device_notes.all()
        )

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
    revision = RevisionSerializer(read_only=True)
    repairs = RepairWithNotesSerializer(many=True, read_only=True)
    exits = ExitSerializer(many=True, read_only=True)
    device_notes = DeviceNoteSerializer(many=True, read_only=True)
    unit_cost = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id",
            "label",
            "ledger_ref",
            "revision",
            "serial",
            "location",
            "purchase",
            "device_notes",
            "status",
            "status_display",
            "reference",
            "repairs",
            "exits",
            "cost_override",
            "unit_cost",
            "touched_at",
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

    `notes` is create-only sugar: it spawns the device's first DeviceNote chunk
    (the intake fault line). Edits go through /device-notes/ — a PATCH sending
    notes is an old client and gets a loud 400, not a silent drop.
    """

    # Lookup fields → which model resolves them.
    LOOKUPS = {"location": Location}

    reference = serializers.PrimaryKeyRelatedField(
        queryset=DeviceReference.objects.all(), required=False, allow_null=True
    )
    revision = serializers.PrimaryKeyRelatedField(
        queryset=Revision.objects.all(), required=False, allow_null=True
    )
    purchase = serializers.PrimaryKeyRelatedField(
        queryset=Purchase.objects.all(), required=False, allow_null=True
    )
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )

    class Meta:
        model = Device
        fields = [
            "reference",
            "revision",
            "serial",
            "location",
            "purchase",
            "notes",
            "status",
            "cost_override",
        ]

    def validate(self, attrs):
        if self.instance and "notes" in self.initial_data:
            raise serializers.ValidationError(
                {"notes": "Device notes are chunked — write via /device-notes/."}
            )
        # Revision must belong to the device's reference — resolve both against
        # what this write leaves in place, not just what it sends.
        revision = attrs.get(
            "revision", getattr(self.instance, "revision", None)
        )
        reference = (
            attrs["reference"]
            if "reference" in attrs
            else getattr(self.instance, "reference", None)
        )
        if revision and (reference is None or revision.reference_id != reference.id):
            raise serializers.ValidationError(
                {"revision": "Revision must belong to the device's reference."}
            )
        return attrs

    def _resolve_lookups(self, validated_data):
        """Pop each provided lookup field, returning {field: instance-or-None}."""
        resolved = {}
        for field, model_cls in self.LOOKUPS.items():
            if field in validated_data:
                name = (validated_data.pop(field) or "").strip()
                resolved[field] = model_cls.objects.get_or_create(name=name)[0] if name else None
        return resolved

    def create(self, validated_data):
        notes = validated_data.pop("notes", "").strip()
        resolved = self._resolve_lookups(validated_data)
        device = Device.objects.create(**validated_data, **resolved)
        if notes:
            device.device_notes.create(position=0, text=notes)
        return device

    def update(self, instance, validated_data):
        validated_data.pop("notes", None)  # unreachable past validate(); belt and braces
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
        notes = validated_data["notes"].strip()
        devices = [
            Device.objects.create(
                purchase=validated_data["purchase"],
                reference=line["reference"],
                location=location,
                status=validated_data["status"],
            )
            for line in validated_data["lines"]
            for _ in range(line["quantity"])
        ]
        if notes:
            for device in devices:
                device.device_notes.create(position=0, text=notes)
        return devices

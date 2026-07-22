"""API serializers.

Inventory list/create + device detail (with nested repairs and steps) on the read
side; device and step write paths for the create/edit modals. Heavier write paths
(measurements, parts, media) stay in the Django admin for now.
"""

from django.utils import timezone
from rest_framework import serializers

from .models import (
    CompPull,
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

# The sheet's refresh discipline: a working comp older than this is due for a re-pull.
STALE_AFTER_DAYS = 60


class LaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lane
        fields = ["id", "name", "policy"]


class CompPullSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = CompPull
        fields = [
            "id",
            "kind",
            "kind_display",
            "median",
            "p25",
            "p75",
            "n",
            "window_days",
            "velocity_per_day",
            "verified",
            "pulled_on",
            "note",
        ]


class DeviceReferenceSerializer(serializers.ModelSerializer):
    """The catalog + price-sheet payload — one row per known model. Read-only.

    Search/filter stays client-side. `stale` / `gap` implement the sheet's two derived
    worklists: stale = latest working pull older than STALE_AFTER_DAYS; gap = no
    working pull at all. Both key off `working` pulls only — parts/service comps don't
    satisfy the buy-decision refresh rule.
    """

    lane = serializers.CharField(source="lane.name", read_only=True)
    comp_pulls = CompPullSerializer(many=True, read_only=True)
    stale = serializers.SerializerMethodField()
    gap = serializers.SerializerMethodField()

    class Meta:
        model = DeviceReference
        fields = [
            "id",
            "lane",
            "brand",
            "name",
            "sku_prefix",
            "memory_config",
            "model_numbers",
            "release_year",
            "configurations",
            "stop_price",
            "stop_note",
            "notes",
            "comp_pulls",
            "stale",
            "gap",
        ]

    def _latest_working(self, obj):
        # comp_pulls is prefetched and ordered -pulled_on, so first match is latest.
        for pull in obj.comp_pulls.all():
            if pull.kind == CompPull.Kind.WORKING:
                return pull
        return None

    def get_stale(self, obj) -> bool:
        pull = self._latest_working(obj)
        if pull is None:
            return False  # that's a gap, not staleness
        return (timezone.localdate() - pull.pulled_on).days > STALE_AFTER_DAYS

    def get_gap(self, obj) -> bool:
        return self._latest_working(obj) is None


class PurchaseSerializer(serializers.ModelSerializer):
    """The buy event, embedded on device payloads and listed on /purchases/."""

    source = serializers.StringRelatedField()
    unit_price = serializers.SerializerMethodField()
    device_count = serializers.IntegerField(source="devices.count", read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id",
            "kind",
            "label",
            "source",
            "order_ref",
            "url",
            "ledger_ref",
            "total_price",
            "purchased_on",
            "arrived_on",
            "from_who",
            "expected_units",
            "device_count",
            "note",
            "unit_price",
        ]

    def get_unit_price(self, obj) -> str | None:
        price = obj.unit_price
        return str(price) if price is not None else None


class PurchaseWriteSerializer(serializers.ModelSerializer):
    """Create / edit a purchase. Source resolves free text to the lookup row."""

    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Purchase
        fields = [
            "id",
            "kind",
            "label",
            "source",
            "order_ref",
            "url",
            "total_price",
            "purchased_on",
            "arrived_on",
            "from_who",
            "expected_units",
            "note",
        ]

    def _resolve_source(self, validated_data):
        if "source" in validated_data:
            name = (validated_data.pop("source") or "").strip()
            validated_data["source"] = (
                Source.objects.get_or_create(name=name)[0] if name else None
            )
        return validated_data

    def create(self, validated_data):
        return super().create(self._resolve_source(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._resolve_source(validated_data))


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


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ["id", "what", "value", "comment"]


class NoteSerializer(serializers.ModelSerializer):
    """A note with its measurements and sub-notes (one level — the domain's max depth)."""

    measurements = MeasurementSerializer(many=True, read_only=True)
    subnotes = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "position",
            "title",
            "text",
            "comment",
            "parent",
            "measurements",
            "subnotes",
        ]

    def get_subnotes(self, obj):
        return NoteSerializer(obj.subnotes.all(), many=True).data


COMPLETED_REPAIR_ERROR = "Repair is completed — un-mark completion to edit it."


class MeasurementWriteSerializer(serializers.ModelSerializer):
    """Create / edit a measurement on a note. No delete path, same as notes."""

    class Meta:
        model = Measurement
        fields = ["id", "note", "what", "value", "comment"]

    def validate(self, attrs):
        note = attrs.get("note") or getattr(self.instance, "note", None)
        if note and note.repair.completed_at:
            raise serializers.ValidationError(COMPLETED_REPAIR_ERROR)
        return attrs


# The 10 phase columns, derived from Repair.PHASES so the two can't drift.
PHASE_FIELDS = [
    f"{key}_{suffix}" for key, _ in Repair.PHASES for suffix in ("done_at", "note")
]


class RepairWithNotesSerializer(serializers.ModelSerializer):
    """A repair plus its phase track and top-level notes (sub-notes nested under each)."""

    current_phase = serializers.CharField(read_only=True)
    notes = serializers.SerializerMethodField()

    class Meta:
        model = Repair
        fields = ["id", "current_phase", "created_at", "completed_at", "comment", "notes", *PHASE_FIELDS]

    def get_notes(self, obj):
        top_level = obj.notes.filter(parent__isnull=True)
        return NoteSerializer(top_level, many=True).data


class RepairWriteSerializer(serializers.ModelSerializer):
    """PATCH path for the phase track, completion mark, and repair-level comment.

    A completed repair is FROZEN: the only writable field is completed_at itself
    (un-marking is the one path back to editing).
    """

    class Meta:
        model = Repair
        fields = ["comment", "completed_at", *PHASE_FIELDS]

    def validate(self, attrs):
        if self.instance and self.instance.completed_at:
            touched = set(attrs) - {"completed_at"}
            if touched:
                raise serializers.ValidationError(COMPLETED_REPAIR_ERROR)
        return attrs


class RepairCreateSerializer(serializers.ModelSerializer):
    """Explicit repair start — a Repair exists because bench work began, never as a
    status carrier."""

    class Meta:
        model = Repair
        fields = ["id", "device", "comment"]


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


class NoteWriteSerializer(serializers.ModelSerializer):
    """Create / edit a note (no delete). Enforces the one-level-deep hierarchy."""

    class Meta:
        model = Note
        fields = ["id", "repair", "parent", "position", "title", "text", "comment"]

    def validate(self, attrs):
        parent = attrs.get("parent") or getattr(self.instance, "parent", None)
        repair = attrs.get("repair") or getattr(self.instance, "repair", None)
        if repair and repair.completed_at:
            raise serializers.ValidationError(COMPLETED_REPAIR_ERROR)
        if parent:
            if parent.parent_id:
                raise serializers.ValidationError(
                    "Notes nest only one level deep — a sub-note cannot have sub-notes."
                )
            if repair and parent.repair_id != repair.id:
                raise serializers.ValidationError(
                    "A sub-note must belong to the same repair as its parent."
                )
        return attrs


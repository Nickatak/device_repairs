"""Bench-work payloads — repairs (phase track), notes, measurements."""

from rest_framework import serializers

from repairs.models import Measurement, Note, Repair

COMPLETED_REPAIR_ERROR = "Repair is completed — un-mark completion to edit it."

# The 10 phase columns, derived from Repair.PHASES so the two can't drift.
PHASE_FIELDS = [
    f"{key}_{suffix}" for key, _ in Repair.PHASES for suffix in ("done_at", "note")
]


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

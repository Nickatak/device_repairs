"""Bench-work payloads — repairs (phase track), notes, measurements, media."""

from django.core.files.base import ContentFile
from rest_framework import serializers

from repairs.exif import extract_taken_at, strip_gps
from repairs.models import Measurement, Media, Note, Repair

COMPLETED_REPAIR_ERROR = "Repair is completed — un-mark completion to edit it."

# The 10 phase columns, derived from Repair.PHASES so the two can't drift.
PHASE_FIELDS = [
    f"{key}_{suffix}" for key, _ in Repair.PHASES for suffix in ("done_at", "note")
]


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ["id", "what", "value", "comment"]


class MediaSerializer(serializers.ModelSerializer):
    """Read shape. `image` is the relative /media/ URL — the browser reaches it
    through the frontend's same-origin proxy, so no absolute backend host here."""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ["id", "image", "caption", "note", "repair", "device_note", "taken_at", "created_at"]

    def get_image(self, obj):
        return obj.image.url


class NoteSerializer(serializers.ModelSerializer):
    """A note with its measurements and sub-notes (one level — the domain's max depth)."""

    measurements = MeasurementSerializer(many=True, read_only=True)
    media = MediaSerializer(many=True, read_only=True)
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
            "media",
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
    media = MediaSerializer(many=True, read_only=True)

    class Meta:
        model = Repair
        fields = ["id", "current_phase", "created_at", "completed_at", "comment", "notes", "media", *PHASE_FIELDS]

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


class MediaWriteSerializer(serializers.ModelSerializer):
    """Upload / correct a photo. No delete path, same as the rest of the log.

    On create the stored file is the GPS-stripped version of the upload and
    `taken_at` comes from its EXIF (see repairs.exif). The image itself is
    immutable after upload — a wrong photo is corrected by re-captioning or
    reparenting; a better photo is a new row.
    """

    class Meta:
        model = Media
        fields = ["id", "image", "caption", "note", "repair", "device_note"]

    def validate(self, attrs):
        if self.instance and "image" in attrs:
            raise serializers.ValidationError(
                "The image file is immutable — upload a new photo instead."
            )

        def resolve(field):
            return attrs[field] if field in attrs else getattr(self.instance, field, None)

        note, repair, device_note = resolve("note"), resolve("repair"), resolve("device_note")
        if sum(1 for parent in (note, repair, device_note) if parent) != 1:
            raise serializers.ValidationError(
                "Media attaches to exactly one of: a note, a repair, OR a device note."
            )
        # The freeze guards the repair log; device notes never freeze.
        owner = repair or (note.repair if note else None)
        if owner and owner.completed_at:
            raise serializers.ValidationError(COMPLETED_REPAIR_ERROR)
        return attrs

    def create(self, validated_data):
        upload = validated_data["image"]
        data = upload.read()
        cleaned = strip_gps(data)
        validated_data["taken_at"] = extract_taken_at(cleaned)
        validated_data["image"] = ContentFile(cleaned, name=upload.name)
        return super().create(validated_data)

    def to_representation(self, instance):
        # Same relative-/media/-URL shape as the read serializer — API consumers
        # see one convention regardless of which payload they're holding.
        rep = super().to_representation(instance)
        rep["image"] = instance.image.url
        rep["taken_at"] = instance.taken_at.isoformat() if instance.taken_at else None
        return rep

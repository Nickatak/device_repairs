"""Stock payloads — minted SKU buckets, their fits links, and intake events."""

from rest_framework import serializers

from repairs.models import DeviceReference, Purchase, Revision, StockIntake, StockItem


class StockIntakeSerializer(serializers.ModelSerializer):
    purchase_label = serializers.CharField(source="purchase.__str__", read_only=True)

    class Meta:
        model = StockIntake
        fields = ["id", "purchase", "purchase_label", "quantity", "note", "created_at"]


class StockItemSerializer(serializers.ModelSerializer):
    """Read payload. `count` is the derived live number (counted tier only);
    fits come as {id, name} pairs so the UI never joins client-side."""

    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    state_display = serializers.CharField(source="get_state_display", read_only=True)
    count = serializers.IntegerField(read_only=True)
    fits_references = serializers.SerializerMethodField()
    fits_revisions = serializers.SerializerMethodField()
    intakes = StockIntakeSerializer(many=True, read_only=True)
    draw_count = serializers.IntegerField(source="draws.count", read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id",
            "name",
            "category",
            "note",
            "mode",
            "mode_display",
            "state",
            "state_display",
            "last_count",
            "counted_at",
            "count",
            "fits_references",
            "fits_revisions",
            "intakes",
            "draw_count",
        ]

    def get_fits_references(self, obj) -> list:
        return [{"id": r.id, "name": str(r)} for r in obj.fits_references.all()]

    def get_fits_revisions(self, obj) -> list:
        return [
            {"id": r.id, "name": f"{r.name} ({r.reference})"}
            for r in obj.fits_revisions.all()
        ]


class StockItemWriteSerializer(serializers.ModelSerializer):
    """Create / edit a bucket. Counting fields stay OUT of this path — the
    count changes only through intakes, draws, and the recount endpoint
    (explicit and forceful, per the design session)."""

    fits_references = serializers.PrimaryKeyRelatedField(
        queryset=DeviceReference.objects.all(), many=True, required=False
    )
    fits_revisions = serializers.PrimaryKeyRelatedField(
        queryset=Revision.objects.all(), many=True, required=False
    )

    class Meta:
        model = StockItem
        fields = [
            "id",
            "name",
            "category",
            "note",
            "mode",
            "state",
            "fits_references",
            "fits_revisions",
        ]


class StockIntakeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockIntake
        fields = ["id", "purchase", "stock_item", "quantity", "note"]

    def validate_purchase(self, purchase):
        if purchase.kind != Purchase.Kind.PARTS:
            raise serializers.ValidationError(
                "Intakes come from parts purchases — device lots become Device rows."
            )
        return purchase


class RecountSerializer(serializers.Serializer):
    """The physical recount: sets the new base and stamps counted_at server-side."""

    count = serializers.IntegerField(min_value=0)

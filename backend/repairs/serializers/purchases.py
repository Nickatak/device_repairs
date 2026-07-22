"""Purchase payloads — the buy event, read and write paths."""

from rest_framework import serializers

from repairs.models import Purchase, Source


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

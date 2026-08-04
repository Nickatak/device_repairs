"""Order payloads — the buy event, read and write paths."""

from rest_framework import serializers

from repairs.models import Device, Order, Source


class OrderSerializer(serializers.ModelSerializer):
    """The buy event, embedded on device payloads and listed on /orders/."""

    source = serializers.StringRelatedField()
    unit_price = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "kind",
            "label",
            "source",
            "order_ref",
            "url",
            "ledger_ref",
            "total_price",
            "ordered_on",
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

    def get_device_count(self, obj) -> int:
        # len(.all()) rides the view's prefetch cache; .count() re-queries.
        return len(obj.devices.all())


class OrderUnitSerializer(serializers.ModelSerializer):
    """Slim device row for the order page's units table — no order echo
    (the parent payload IS the order)."""

    label = serializers.SerializerMethodField()
    location = serializers.StringRelatedField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    repair_count = serializers.IntegerField(source="repairs.count", read_only=True)
    unit_cost = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id",
            "label",
            "ledger_ref",
            "serial",
            "status",
            "status_display",
            "location",
            "repair_count",
            "cost_override",
            "unit_cost",
        ]

    def get_label(self, obj) -> str:
        return str(obj)

    def get_unit_cost(self, obj) -> str | None:
        cost = obj.unit_cost
        return str(cost) if cost is not None else None


class OrderDetailSerializer(OrderSerializer):
    """The order page payload — the buy event plus its linked device rows."""

    devices = OrderUnitSerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = [*OrderSerializer.Meta.fields, "devices"]


class OrderWriteSerializer(serializers.ModelSerializer):
    """Create / edit a order. Source resolves free text to the lookup row."""

    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "kind",
            "label",
            "source",
            "order_ref",
            "url",
            "total_price",
            "ordered_on",
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

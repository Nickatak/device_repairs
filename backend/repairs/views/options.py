"""The cross-domain combobox aggregate — every lookup pool the create/edit modals need."""

from django.db.models import F, Max
from rest_framework.response import Response
from rest_framework.views import APIView

from repairs.models import Device, DeviceReference, Exit, Location, Purchase, Source
from repairs.serializers import PurchaseSerializer


class OptionsView(APIView):
    """Existing lookup values, for combo-box datalists in the create/edit modal."""

    def get(self, request):
        return Response(
            {
                # Catalog rows for the device form's reference combobox — light
                # projection; the full price-sheet payload stays on /reference/.
                # Most-recently-USED first (highest linked device id — devices
                # carry no timestamp, so row id is the recency proxy); never-used
                # rows follow alphabetically. Revisions ride along so the form's
                # revision picker can filter to the chosen reference.
                "references": [
                    {
                        "id": ref.id,
                        "brand": ref.brand,
                        "name": ref.name,
                        "sku_prefix": ref.sku_prefix,
                        "model_numbers": ref.model_numbers,
                        "revisions": [
                            {"id": rev.id, "name": rev.name}
                            for rev in ref.revisions.all()
                        ],
                    }
                    for ref in DeviceReference.objects.annotate(
                        last_used=Max("units__id")
                    )
                    .order_by(F("last_used").desc(nulls_last=True), "brand", "name")
                    .prefetch_related("revisions")
                ],
                # Most-recently-used first (same device-id proxy as references).
                "locations": list(
                    Location.objects.annotate(last_used=Max("devices__id"))
                    .order_by(F("last_used").desc(nulls_last=True), "name")
                    .values_list("name", flat=True)
                ),
                "sources": list(Source.objects.values_list("name", flat=True)),
                # Shared counterparty pool: everyone seen in purchases' from_who
                # or exits' to_who feeds both comboboxes.
                "people": sorted(
                    set(
                        Purchase.objects.exclude(from_who="").values_list(
                            "from_who", flat=True
                        )
                    )
                    | set(Exit.objects.exclude(to_who="").values_list("to_who", flat=True))
                ),
                # Buy events for the device form's purchase combobox, most
                # recently placed first — device lots only; parts purchases
                # never hold devices. Explicit nulls_last: Postgres would
                # otherwise lead a DESC sort with the undated own-stock rows.
                "purchases": PurchaseSerializer(
                    Purchase.objects.filter(kind=Purchase.Kind.DEVICE)
                    .select_related("source")
                    .prefetch_related("devices")
                    .order_by(F("purchased_on").desc(nulls_last=True), "-id"),
                    many=True,
                ).data,
                "statuses": [
                    {"value": value, "label": label}
                    for value, label in Device.Status.choices
                ],
            }
        )

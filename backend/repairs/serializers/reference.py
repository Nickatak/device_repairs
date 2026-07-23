"""Price-sheet catalog payloads — lanes, references, comp pulls. Read-only API."""

from django.utils import timezone
from rest_framework import serializers

from repairs.models import CompPull, DeviceReference, Issue, Lane

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


class IssueSerializer(serializers.ModelSerializer):
    verdict_display = serializers.CharField(source="get_verdict_display", read_only=True)

    class Meta:
        model = Issue
        fields = ["id", "verdict", "verdict_display", "title", "note", "position"]


class DeviceReferenceSerializer(serializers.ModelSerializer):
    """The catalog + price-sheet payload — one row per known model. Read-only.

    Search/filter stays client-side. `stale` / `gap` implement the sheet's two derived
    worklists: stale = latest working pull older than STALE_AFTER_DAYS; gap = no
    working pull at all. Both key off `working` pulls only — parts/service comps don't
    satisfy the buy-decision refresh rule.
    """

    lane = serializers.CharField(source="lane.name", read_only=True)
    comp_pulls = CompPullSerializer(many=True, read_only=True)
    issues = IssueSerializer(many=True, read_only=True)
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
            "issues",
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

"""Admin — the single-user back-of-house for typing a repair as it happens.

Django admin can't nest inlines, so the flow is two-level: build a Repair with its Notes
inline, then open a Note to add its Measurements / Parts / Media.
"""

from django.contrib import admin

from .models import (
    CompPull,
    Device,
    DeviceReference,
    Lane,
    Location,
    Measurement,
    Media,
    Note,
    Part,
    Purchase,
    Repair,
    Source,
)


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0
    fields = ("position", "title", "text")
    show_change_link = True  # click through to add measurements / parts / media


class RepairMediaInline(admin.TabularInline):
    model = Media
    fk_name = "repair"
    extra = 0


class NoteMediaInline(admin.TabularInline):
    model = Media
    fk_name = "note"
    extra = 0


class MeasurementInline(admin.TabularInline):
    model = Measurement
    extra = 0


class PartInline(admin.TabularInline):
    model = Part
    extra = 0


@admin.register(Repair)
class RepairAdmin(admin.ModelAdmin):
    list_display = ("__str__", "device", "current_phase", "completed_at", "created_at")
    search_fields = ("device__reference__brand", "device__reference__name", "comment")
    inlines = (NoteInline, RepairMediaInline)
    fieldsets = (
        (None, {"fields": ("device", "comment")}),
        (
            "Phase track (Teardown → Wash → Repair → Re-assemble → Verify)",
            {
                "fields": tuple(
                    (f"{key}_done_at", f"{key}_note") for key, _ in Repair.PHASES
                )
            },
        ),
        (
            "Completion (manual — unchecked phases on a completed repair did NOT happen)",
            {"fields": ("completed_at",)},
        ),
    )


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "repair", "parent", "position")
    list_filter = ("repair",)
    search_fields = ("title", "text", "comment")
    inlines = (MeasurementInline, PartInline, NoteMediaInline)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "location", "purchase", "serial")
    list_filter = ("status", "location", "purchase__source")
    search_fields = ("reference__brand", "reference__name", "serial")
    autocomplete_fields = ("location", "reference", "purchase")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "source", "total_price", "expected_units", "purchased_on", "created_at")
    list_filter = ("kind",)
    search_fields = ("label", "order_ref", "ledger_ref", "source__name", "note")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class CompPullInline(admin.TabularInline):
    """Newest-first pull history on the catalog row. Append rows; don't edit history."""

    model = CompPull
    extra = 0
    fields = ("kind", "median", "p25", "p75", "n", "window_days", "velocity_per_day", "verified", "pulled_on", "note")


@admin.register(Lane)
class LaneAdmin(admin.ModelAdmin):
    list_display = ("name", "reference_count")
    search_fields = ("name",)

    def reference_count(self, obj):
        return obj.references.count()


@admin.register(DeviceReference)
class DeviceReferenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "lane", "stop_price", "release_year", "sku_prefix", "model_numbers")
    list_filter = ("lane", "brand")
    search_fields = ("brand", "name", "model_numbers", "sku_prefix", "configurations")
    ordering = ("lane__name", "brand", "release_year", "name")
    autocomplete_fields = ("lane",)
    inlines = (CompPullInline,)


@admin.register(CompPull)
class CompPullAdmin(admin.ModelAdmin):
    list_display = ("reference", "kind", "median", "n", "velocity_per_day", "verified", "pulled_on")
    list_filter = ("kind", "verified", "reference__lane")
    search_fields = ("reference__brand", "reference__name", "note")
    date_hierarchy = "pulled_on"
    autocomplete_fields = ("reference",)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    search_fields = ("name",)


admin.site.site_header = "Repair working log"
admin.site.site_title = "Repair log"
admin.site.index_title = "Back of house"

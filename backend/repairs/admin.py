"""Admin — the single-user back-of-house for typing a repair as it happens.

Django admin can't nest inlines, so the flow is two-level: build a Repair with its Notes
inline, then open a Note to add its Measurements / Parts / Media.
"""

from django.contrib import admin

from .models import (
    CompPull,
    Device,
    DeviceReference,
    Issue,
    Lane,
    Location,
    Measurement,
    Media,
    Note,
    Part,
    Order,
    Repair,
    Revision,
    Source,
    StockIntake,
    StockItem,
    Variant,
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
    list_display = ("__str__", "status", "location", "order", "serial")
    list_filter = ("status", "location", "order__source")
    search_fields = ("reference__brand", "reference__name", "serial")
    autocomplete_fields = ("location", "reference", "order")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "source", "total_price", "expected_units", "ordered_on", "created_at")
    list_filter = ("kind",)
    search_fields = ("label", "order_ref", "ledger_ref", "source__name", "note")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class IssueInline(admin.TabularInline):
    """The symptom-decomposition table: category | fault | cause | verdict | note."""

    model = Issue
    extra = 0
    fields = ("category", "fault", "cause", "verdict", "note", "position")


class VariantInline(admin.TabularInline):
    """Special editions of this model — same model number, different shell/price band."""

    model = Variant
    extra = 0
    fields = ("name", "note", "position")


class RevisionInline(admin.TabularInline):
    """Board revisions of this model — the compatibility axis (JDM-055, BDM-020)."""

    model = Revision
    extra = 0
    fields = ("name", "note", "position")


class CompPullInline(admin.TabularInline):
    """Newest-first pull history on the catalog row. Append rows; don't edit history."""

    model = CompPull
    extra = 0
    fields = ("variant", "kind", "median", "p25", "p75", "n", "window_days", "velocity_per_day", "verified", "pulled_on", "note")


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
    inlines = (RevisionInline, VariantInline, IssueInline, CompPullInline)


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


class StockIntakeInline(admin.TabularInline):
    model = StockIntake
    extra = 0
    fields = ("order", "quantity", "note", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("order",)


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "mode", "state", "count", "last_count", "counted_at")
    list_filter = ("mode", "state", "category")
    search_fields = ("name", "category", "note")
    filter_horizontal = ("fits_references", "fits_revisions")
    inlines = (StockIntakeInline,)


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("name", "reference", "position")
    list_filter = ("reference__lane",)
    search_fields = ("name", "reference__brand", "reference__name")
    autocomplete_fields = ("reference",)


admin.site.site_header = "Repair working log"
admin.site.site_title = "Repair log"
admin.site.index_title = "Back of house"

from django.contrib import admin

from .models import DriverNumberMap, SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source",
        "job",
        "status",
        "started_at",
        "finished_at",
        "created",
        "updated",
        "skipped",
    )
    list_filter = ("status", "source", "job", "started_at")
    search_fields = ("source", "job")
    date_hierarchy = "started_at"
    readonly_fields = [f.name for f in SyncRun._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(DriverNumberMap)
class DriverNumberMapAdmin(admin.ModelAdmin):
    list_display = ("season_year", "driver_number", "driver")
    list_filter = ("season_year",)
    search_fields = ("driver__family_name", "driver__code")
    raw_id_fields = ("driver",)

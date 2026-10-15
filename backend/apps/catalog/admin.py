from django.contrib import admin

from .models import (
    Circuit,
    Constructor,
    ConstructorSeason,
    Driver,
    PointsSystem,
    QualifyingResult,
    Result,
    Round,
    Season,
    Session,
)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("year", "name")
    search_fields = ("year", "name")


@admin.register(PointsSystem)
class PointsSystemAdmin(admin.ModelAdmin):
    list_display = ("season", "session_type", "fastest_lap_point", "fastest_lap_min_position")
    list_filter = ("session_type", "fastest_lap_point")
    list_select_related = ("season",)


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = ("name", "locality", "country", "timezone", "length_m")
    list_filter = ("country",)
    search_fields = ("name", "slug", "locality", "country", "jolpica_id")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Constructor)
class ConstructorAdmin(admin.ModelAdmin):
    list_display = ("name", "nationality", "jolpica_id")
    list_filter = ("nationality",)
    search_fields = ("name", "slug", "jolpica_id")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ConstructorSeason)
class ConstructorSeasonAdmin(admin.ModelAdmin):
    list_display = ("constructor", "season", "display_name", "color_hex")
    list_filter = ("season",)
    search_fields = ("constructor__name", "display_name")
    list_select_related = ("constructor", "season")
    autocomplete_fields = ("constructor",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("family_name", "given_name", "code", "permanent_number", "nationality")
    list_filter = ("nationality",)
    search_fields = ("search_name", "family_name", "given_name", "code", "slug", "jolpica_id")
    readonly_fields = ("search_name",)


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ("season", "round", "name", "circuit", "date", "is_cancelled")
    list_filter = ("season", "is_cancelled")
    search_fields = ("name", "circuit__name")
    list_select_related = ("season", "circuit")
    autocomplete_fields = ("circuit",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("round", "type", "start_utc", "end_utc", "status")
    list_filter = ("type", "status", "round__season")
    search_fields = ("round__name",)
    list_select_related = ("round", "round__season")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "position_text",
        "driver",
        "constructor",
        "points",
        "status",
        "manual_override",
    )
    list_filter = ("session__type", "session__round__season", "manual_override")
    search_fields = ("driver__search_name", "constructor__name")
    list_select_related = ("session", "session__round", "driver", "constructor")
    raw_id_fields = ("session", "driver", "constructor")


@admin.register(QualifyingResult)
class QualifyingResultAdmin(admin.ModelAdmin):
    list_display = ("session", "position", "driver", "constructor", "q1_ms", "q2_ms", "q3_ms")
    list_filter = ("session__round__season",)
    search_fields = ("driver__search_name", "constructor__name")
    list_select_related = ("session", "session__round", "driver", "constructor")
    raw_id_fields = ("session", "driver", "constructor")

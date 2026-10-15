from django.contrib import admin

from .models import ConstructorStanding, DriverStanding


@admin.register(DriverStanding)
class DriverStandingAdmin(admin.ModelAdmin):
    list_display = ("season", "after_round", "position_text", "driver", "points", "wins", "podiums")
    list_filter = ("season", "after_round")
    list_select_related = ("season", "driver")
    raw_id_fields = ("season", "driver")
    search_fields = ("driver__family_name", "driver__given_name")


@admin.register(ConstructorStanding)
class ConstructorStandingAdmin(admin.ModelAdmin):
    list_display = (
        "season",
        "after_round",
        "position_text",
        "constructor",
        "points",
        "wins",
        "podiums",
    )
    list_filter = ("season", "after_round")
    list_select_related = ("season", "constructor")
    raw_id_fields = ("season", "constructor")
    search_fields = ("constructor__name",)

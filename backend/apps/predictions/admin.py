from django.contrib import admin

from .models import League, LeagueMembership, Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "round", "points", "created_at")
    list_filter = ("round__season",)
    list_select_related = ("user", "round__season")
    raw_id_fields = ("user", "round", "p1", "p2", "p3", "pole", "fastest_lap")
    readonly_fields = ("created_at", "updated_at")


class LeagueMembershipInline(admin.TabularInline):
    model = LeagueMembership
    extra = 0
    raw_id_fields = ("user",)


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "invite_code", "created_at")
    search_fields = ("name", "invite_code")
    raw_id_fields = ("owner",)
    inlines = [LeagueMembershipInline]

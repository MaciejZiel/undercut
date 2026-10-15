from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Favorite, User


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    list_display = ("username", "email", "display_name", "email_verified", "is_demo", "is_staff")
    list_filter = (*UserAdmin.list_filter, "email_verified", "is_demo")
    search_fields = (*UserAdmin.search_fields, "display_name")
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "Undercut",
            {"fields": ("display_name", "email_verified", "timezone", "theme", "is_demo")},
        ),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "driver", "constructor", "created_at")
    raw_id_fields = ("user", "driver", "constructor")

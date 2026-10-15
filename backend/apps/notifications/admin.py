from django.contrib import admin

from .models import NotificationPref


@admin.register(NotificationPref)
class NotificationPrefAdmin(admin.ModelAdmin):
    list_display = ("user", "race_result_email", "updated_at")
    exclude = ("unsubscribe_token",)
    readonly_fields = ("user",)

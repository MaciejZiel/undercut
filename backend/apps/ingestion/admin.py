from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from . import services
from .models import DriverNumberMap, SyncRun


class ResyncForm(forms.Form):
    year = forms.IntegerField(min_value=1950, max_value=2100)
    round = forms.IntegerField(min_value=1, max_value=40)
    analytics = forms.BooleanField(required=False, initial=True, label="Also OpenF1 analytics")


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
    change_list_template = "admin/ingestion/syncrun/change_list.html"

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        extra = [
            path(
                "resync/",
                self.admin_site.admin_view(self.resync_view),
                name="ingestion_syncrun_resync",
            )
        ]
        return extra + super().get_urls()

    def resync_view(self, request):
        if not self.has_change_permission(request):
            return redirect("admin:index")
        form = ResyncForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                queued = services.request_round_resync(
                    form.cleaned_data["year"],
                    form.cleaned_data["round"],
                    analytics=form.cleaned_data["analytics"],
                )
            except services.RoundNotFound as exc:
                form.add_error(None, str(exc))
            else:
                self.message_user(
                    request,
                    f"Queued {queued['SessionResultsDue']} results sync(s), "
                    f"{queued['PracticeResultsDue']} practice import(s) and "
                    f"{queued['AnalyticsDue']} analytics import(s).",
                    messages.SUCCESS,
                )
                return redirect(reverse("admin:ingestion_syncrun_changelist"))
        context = {**self.admin_site.each_context(request), "title": "Rerun a round", "form": form}
        return TemplateResponse(request, "admin/ingestion/syncrun/resync.html", context)


@admin.register(DriverNumberMap)
class DriverNumberMapAdmin(admin.ModelAdmin):
    list_display = ("season_year", "driver_number", "driver")
    list_filter = ("season_year",)
    search_fields = ("driver__family_name", "driver__code")
    raw_id_fields = ("driver",)

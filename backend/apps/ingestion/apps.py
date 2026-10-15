from django.apps import AppConfig
from django.db.models.signals import post_save


class IngestionConfig(AppConfig):
    name = "apps.ingestion"

    def ready(self):
        from . import alerts, handlers
        from .models import SyncRun

        handlers.register()
        post_save.connect(
            alerts.on_sync_run_saved, sender=SyncRun, dispatch_uid="sync-failure-alert"
        )

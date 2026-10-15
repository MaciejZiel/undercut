from django.apps import AppConfig


class IngestionConfig(AppConfig):
    name = "apps.ingestion"

    def ready(self):
        from . import handlers

        handlers.register()

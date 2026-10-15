from django.apps import AppConfig


class PredictionsConfig(AppConfig):
    name = "apps.predictions"

    def ready(self):
        from . import exports, handlers

        handlers.register_handlers()
        exports.register()

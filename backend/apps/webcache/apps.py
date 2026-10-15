from django.apps import AppConfig


class WebcacheConfig(AppConfig):
    name = "apps.webcache"

    def ready(self):
        from . import handlers

        handlers.register()

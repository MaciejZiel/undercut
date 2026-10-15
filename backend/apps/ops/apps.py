from django.apps import AppConfig


class OpsConfig(AppConfig):
    name = "apps.ops"

    def ready(self) -> None:
        from . import checks, handlers  # noqa: F401  (checks register the deploy checks)

        handlers.register()

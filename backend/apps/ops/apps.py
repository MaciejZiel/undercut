from django.apps import AppConfig


class OpsConfig(AppConfig):
    name = "apps.ops"

    def ready(self) -> None:
        from . import checks  # noqa: F401  (registers the deploy checks)

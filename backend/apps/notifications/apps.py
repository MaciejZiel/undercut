from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "apps.notifications"

    def ready(self) -> None:
        from apps.accounts.exports import register_export_provider

        from . import handlers, services

        handlers.register_handlers()
        register_export_provider("notifications", services.export_user_data)

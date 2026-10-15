from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"

    def ready(self) -> None:
        from allauth.account import signals

        from . import handlers, receivers

        handlers.register_handlers()
        for signal in (
            signals.email_confirmed,
            signals.email_changed,
            signals.email_added,
            signals.email_removed,
        ):
            signal.connect(receivers.sync_email_verified, dispatch_uid="accounts-sync-email")

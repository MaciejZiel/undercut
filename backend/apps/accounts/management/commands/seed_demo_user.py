from django.core.management.base import BaseCommand

from apps.accounts import services


class Command(BaseCommand):
    help = (
        "Create (or repair) the shared demo account: locked, no password login, with starting "
        "favourites. Safe to run repeatedly; it also resets the account to its initial state."
    )

    def handle(self, *args, **options):
        user = services.ensure_demo_user()
        services.reset_demo_account()
        self.stdout.write(
            self.style.SUCCESS(f"Demo account ready: {user.display_name} (#{user.pk})")
        )

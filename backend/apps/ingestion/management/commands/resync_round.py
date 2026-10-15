from django.core.management.base import BaseCommand, CommandError

from apps.ingestion import services


class Command(BaseCommand):
    help = (
        "Queue a fresh sync of one round (results, standings, OpenF1 analytics). "
        "The outbox worker does the work; safe to repeat."
    )

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("round", type=int)
        parser.add_argument(
            "--no-analytics", action="store_true", help="Skip the OpenF1 analytics import."
        )

    def handle(self, *args, **options):
        try:
            queued = services.request_round_resync(
                options["year"], options["round"], analytics=not options["no_analytics"]
            )
        except services.RoundNotFound as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Queued {queued['SessionResultsDue']} results sync(s) and "
            f"{queued['AnalyticsDue']} analytics import(s) for {options['year']} round "
            f"{options['round']}."
        )

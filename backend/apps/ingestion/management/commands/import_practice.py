from django.core.management.base import BaseCommand

from apps.ingestion.openf1.client import OpenF1Client
from apps.ingestion.openf1.practice import import_practice


class Command(BaseCommand):
    help = (
        "Import practice results from OpenF1 (2023 onwards) for sessions that have none. "
        "A few requests per session; safe to repeat."
    )

    def add_arguments(self, parser):
        parser.add_argument("--since", type=int, default=2023)
        parser.add_argument("--until", type=int, help="Last year (default: this year).")
        parser.add_argument(
            "--all", action="store_true", help="Also refresh sessions that already have results."
        )

    def handle(self, *args, **options):
        import datetime as dt

        last = options["until"] or dt.date.today().year
        outcomes = import_practice(
            OpenF1Client(),
            years=list(range(options["since"], last + 1)),
            only_missing=not options["all"],
        )
        rows = sum(o.rows for o in outcomes)
        problems = [p for o in outcomes for p in o.problems]
        self.stdout.write(f"{len(outcomes)} session(s), {rows} row(s), {len(problems)} problem(s)")
        for line in problems[:40]:
            self.stdout.write(f"  {line}")

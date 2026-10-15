from django.core.management.base import BaseCommand

from apps.ingestion.openf1.client import OpenF1Client
from apps.ingestion.openf1.outline import import_outlines


class Command(BaseCommand):
    help = (
        "Draw track outlines for circuits that have none, from one lap of the race winner in "
        "OpenF1 (2023 onwards). Three small requests per circuit; safe to repeat."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, action="append", help="Only this year (repeatable)."
        )
        parser.add_argument("--round", type=int, dest="round_number", help="Only this round.")
        parser.add_argument("--force", action="store_true", help="Redraw circuits that have one.")

    def handle(self, *args, **options):
        summary = import_outlines(
            OpenF1Client(),
            years=options["year"],
            round_number=options["round_number"],
            force=options["force"],
        )
        self.stdout.write(
            f"written {len(summary.written)}, already had one {len(summary.skipped)}, "
            f"failed {len(summary.failed)}"
        )
        for line in summary.written:
            self.stdout.write(f"  drawn: {line}")
        for line in summary.failed:
            self.stdout.write(f"  FAILED: {line}")

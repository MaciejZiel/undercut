import datetime as dt
import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ingestion.models import SyncRun
from apps.ingestion.openf1.client import OpenF1Client
from apps.ingestion.openf1.importer import run_import

FIRST_SEASON = 2023  # OpenF1 has no data before this
VALID_TYPES = {"FP1", "FP2", "FP3", "SQ", "SPRINT", "Q", "RACE"}


def _round_arg(value: str) -> tuple[int, int]:
    try:
        year, number = value.split(":")
        return int(year), int(number)
    except ValueError as exc:
        raise CommandError("--round must look like YEAR:NUMBER, e.g. 2024:1") from exc


class Command(BaseCommand):
    help = (
        "Import race analytics (laps, stints, pit stops, positions, intervals, weather, race "
        "control) from OpenF1. Resumable and idempotent; paced at 80% of the free rate limit."
    )

    def add_arguments(self, parser):
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument("--year", type=int, help="One season.")
        scope.add_argument("--since", type=int, help="Every season from this year to now.")
        scope.add_argument("--round", dest="round_", metavar="YEAR:N", help="One round.")
        scope.add_argument("--session-key", type=int, help="One OpenF1 session.")
        parser.add_argument("--types", help="Comma separated, e.g. RACE,Q,SPRINT (default: all).")
        parser.add_argument("--force", action="store_true", help="Re-import finished sessions.")
        parser.add_argument("--dry-run", action="store_true", help="Do everything, then roll back.")

    def handle(self, *args, **options):
        started = time.monotonic()
        years: list[int] | None = None
        round_number = None
        if options["year"]:
            years = [options["year"]]
        elif options["since"]:
            years = list(range(max(options["since"], FIRST_SEASON), timezone.now().year + 1))
        elif options["round_"]:
            year, round_number = _round_arg(options["round_"])
            years = [year]
        types = None
        if options["types"]:
            types = frozenset(t.strip().upper() for t in options["types"].split(",") if t.strip())
            if not types <= VALID_TYPES:
                raise CommandError(f"Unknown session types: {sorted(types - VALID_TYPES)}")
        if years and any(y < FIRST_SEASON for y in years):
            raise CommandError(f"OpenF1 has no data before {FIRST_SEASON}.")

        client = OpenF1Client()
        try:
            summary = run_import(
                client,
                years=years,
                round_number=round_number,
                session_key=options["session_key"],
                types=types,
                force=options["force"],
                dry_run=options["dry_run"],
                report=self.stdout.write,
            )
        except KeyboardInterrupt:
            self.stderr.write("Interrupted; progress is saved, run again to resume.")
            raise
        run = summary.run
        label = " (dry run, rolled back)" if summary.dry_run else ""
        self.stdout.write(f"SyncRun #{run.pk}: {run.status}{label}")
        self.stdout.write(f"  sessions imported: {len(summary.imported)}")
        for reason, items in summary.skipped.items():
            self.stdout.write(f"  skipped ({reason}): {len(items)}")
        for table, count in sorted(summary.rows.items()):
            self.stdout.write(f"  {table:18} rows={count}")
        self.stdout.write(f"  rows without a usable driver/value: {summary.unmapped_rows}")
        endpoints = ", ".join(f"{k}={v}" for k, v in sorted(summary.by_endpoint.items()))
        self.stdout.write(f"  requests: {summary.requests} ({endpoints})")
        for note in summary.notes:
            self.stdout.write(f"  note: {note}")
        for err in run.errors:
            self.stderr.write(f"  ERROR {err.get('type')}: {err}")
        elapsed = dt.timedelta(seconds=round(time.monotonic() - started))
        self.stdout.write(f"Done in {elapsed}.")
        if run.status == SyncRun.Status.FAILED:
            raise CommandError("Import aborted; see errors above.")

import tempfile
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.jolpica.dump import DumpError, download_dump
from apps.ingestion.jolpica.importer import run_import


class Command(BaseCommand):
    help = "Import F1 history from the Jolpica CSV dump (zip or extracted directory)."

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument("--dump", type=Path, help="Path to the dump zip or extracted folder.")
        source.add_argument("--download", action="store_true", help="Download the delayed dump.")
        parser.add_argument("--from-year", type=int)
        parser.add_argument("--to-year", type=int)
        parser.add_argument("--dry-run", action="store_true", help="Do everything, then roll back.")

    def handle(self, *args, **options):
        started = time.monotonic()
        try:
            if options["download"]:
                with tempfile.TemporaryDirectory(prefix="jolpica-dl-") as tmp:
                    target = download_dump(Path(tmp) / "jolpica-f1-csv.zip")
                    self.stdout.write(f"Downloaded {target.stat().st_size / 1e6:.1f} MB.")
                    result = self._run(target, options)
            else:
                if not options["dump"].exists():
                    raise CommandError(f"{options['dump']} does not exist.")
                result = self._run(options["dump"], options)
        except DumpError as exc:
            raise CommandError(str(exc)) from exc
        run, totals = result
        label = " (dry run, rolled back)" if options["dry_run"] else ""
        self.stdout.write(f"SyncRun #{run.pk}: {run.status}{label}")
        for name, c in totals.items():
            self.stdout.write(
                f"  {name:20} created={c.created} updated={c.updated} "
                f"unchanged={c.unchanged} skipped_manual={c.skipped_manual}"
            )
        for err in run.errors:
            self.stderr.write(f"  ERROR {err['round']}: {err['error']}")
        self.stdout.write(f"Done in {time.monotonic() - started:.1f}s.")

    def _run(self, path, options):
        return run_import(
            path,
            from_year=options["from_year"],
            to_year=options["to_year"],
            dry_run=options["dry_run"],
            report=self.stdout.write,
        )

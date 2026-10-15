from django.core.management.base import BaseCommand

from apps.ingestion.circuit_geojson import import_geojson


class Command(BaseCommand):
    help = (
        "Draw track outlines from the bundled f1-circuits GeoJSON (MIT) for circuits that have "
        "none and that OpenF1 does not cover. Makes no network requests; safe to repeat."
    )

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Redraw circuits that have one.")

    def handle(self, *args, **options):
        summary = import_geojson(force=options["force"])
        self.stdout.write(
            f"written {len(summary.written)}, already had one {len(summary.skipped)}, "
            f"failed {len(summary.failed)}"
        )
        for line in summary.written:
            self.stdout.write(f"  drawn: {line}")
        for line in summary.failed:
            self.stdout.write(f"  FAILED: {line}")

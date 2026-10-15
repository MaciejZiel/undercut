import time

from django.core.management.base import BaseCommand

from apps.events.scheduler import run_due
from apps.ops.heartbeat import SCHEDULER, beat


class Command(BaseCommand):
    help = "Publish events for recurring jobs that are due."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Check once and exit.")
        parser.add_argument("--interval", type=float, default=30.0, help="Check interval, s.")

    def handle(self, *args, **options):
        while True:
            beat(SCHEDULER)
            fired = run_due()
            if fired:
                self.stdout.write(f"Published {fired} scheduled event(s).")
            if options["once"]:
                return
            time.sleep(options["interval"])

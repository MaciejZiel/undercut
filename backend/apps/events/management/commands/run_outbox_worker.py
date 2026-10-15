import time

from django.core.management.base import BaseCommand

from apps.events.worker import process_batch
from apps.ops.heartbeat import OUTBOX_WORKER, beat


class Command(BaseCommand):
    help = "Deliver outbox events to their handlers."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process due events and exit.")
        parser.add_argument("--interval", type=float, default=1.0, help="Idle poll interval, s.")

    def handle(self, *args, **options):
        while True:
            beat(OUTBOX_WORKER)
            handled = process_batch()
            if options["once"]:
                self.stdout.write(f"Handled {handled} event(s).")
                return
            if handled == 0:
                time.sleep(options["interval"])

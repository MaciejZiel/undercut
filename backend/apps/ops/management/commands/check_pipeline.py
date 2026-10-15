import json
import sys

from django.core.management.base import BaseCommand

from apps.ops.status import pipeline_problems


class Command(BaseCommand):
    help = (
        "Exit non-zero when the pipeline needs attention: dead or stuck outbox events, a stale "
        "heartbeat, or a finished race without final results. Meant for cron."
    )

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Print the problems as JSON.")

    def handle(self, *args, **options):
        problems = pipeline_problems()
        if options["json"]:
            self.stdout.write(
                json.dumps({"ok": not problems, "problems": [p.__dict__ for p in problems]})
            )
        elif problems:
            for problem in problems:
                self.stdout.write(f"PROBLEM {problem.code}: {problem.message}")
        else:
            self.stdout.write("OK")
        if problems:
            sys.exit(1)

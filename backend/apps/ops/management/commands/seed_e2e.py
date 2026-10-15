"""Prepare deterministic data for the end-to-end run (GitHub Actions only).

Picks the latest non-cancelled round of the newest season that has race results and gives it a
qualifying and a race session in the near future, so the prediction game has an open round
whatever today's date is. Nothing is deleted; only the times and the status of these two
sessions are rewritten, so the command can be repeated freely. With ``--lock`` the qualifying
start is moved into the past instead, which closes the round (used to test the server lock).

This ops command reads catalog models directly. That is the documented exception to the module
rules: it is a test fixture loader, not part of the application.

The last line of the output is JSON with the keys year, round, qualifying_start and locked.
"""

import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Round, Session

QUALIFYING_OPENS_IN = timedelta(days=2)
QUALIFYING_LENGTH = timedelta(hours=1)
RACE_STARTS_IN = timedelta(days=3)
RACE_LENGTH = timedelta(hours=2)
LOCKED_STARTED_AGO = timedelta(minutes=30)


def pick_round() -> Round | None:
    """Newest season with race results, its last real round; any real round as a fallback."""
    real = Round.objects.filter(is_cancelled=False, round__isnull=False)
    with_results = real.filter(
        sessions__type=Session.Type.RACE, sessions__results__isnull=False
    ).distinct()
    ordering = ("-season__year", "-round")
    return with_results.order_by(*ordering).first() or real.order_by(*ordering).first()


def _set_session(round_: Round, session_type: str, start, length: timedelta) -> None:
    Session.objects.update_or_create(
        round=round_,
        type=session_type,
        defaults={
            "start_utc": start,
            "end_utc": start + length,
            "status": Session.Status.SCHEDULED,
        },
    )


class Command(BaseCommand):
    help = "Open (or with --lock close) the prediction round used by the end-to-end tests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lock",
            action="store_true",
            help="Move the qualifying start into the past so predictions are closed.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            # It rewrites session times of a real round: never on a production database.
            raise CommandError("seed_e2e only runs with DJANGO_DEBUG=true (the e2e stack).")
        locked = options["lock"]
        now = timezone.now()
        with transaction.atomic():
            round_ = pick_round()
            if round_ is None:
                raise CommandError("No round in the database. Run import_history first.")
            qualifying_start = now - LOCKED_STARTED_AGO if locked else now + QUALIFYING_OPENS_IN
            _set_session(round_, Session.Type.Q, qualifying_start, QUALIFYING_LENGTH)
            _set_session(round_, Session.Type.RACE, now + RACE_STARTS_IN, RACE_LENGTH)
        year = round_.season.year
        state = "locked" if locked else "open"
        self.stdout.write(f"Round {round_.round} of {year} ({round_.name}): {state}")
        self.stdout.write(
            json.dumps(
                {
                    "year": year,
                    "round": round_.round,
                    "qualifying_start": qualifying_start.isoformat(),
                    "locked": locked,
                }
            )
        )

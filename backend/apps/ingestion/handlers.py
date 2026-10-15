"""Event handlers and schedule providers of the ingestion module (registered in AppConfig)."""

from __future__ import annotations

import datetime as dt
import logging

from django.utils import timezone

from apps.catalog import scheduling
from apps.events.registry import subscribe
from apps.events.scheduler import DueEvent, register_provider

from .jolpica import sync
from .jolpica.client import shared_client
from .openf1.client import OpenF1Client
from .openf1.importer import run_import

log = logging.getLogger(__name__)

RESULTS_AFTER = dt.timedelta(hours=1)  # first poll one hour after the session ends
RESULTS_UNTIL = dt.timedelta(hours=12)  # then hourly, give up after twelve hours
CORRECTIONS_WINDOW = dt.timedelta(days=8)

# OpenF1 analytics: first try two hours after the session, then every two hours for a day. A
# session that was already imported is skipped by the importer (a couple of cheap requests).
ANALYTICS_AFTER = dt.timedelta(hours=2)
ANALYTICS_UNTIL = dt.timedelta(hours=24)
ANALYTICS_TYPES = ("RACE", "SPRINT")


def results_due(now: dt.datetime):
    """One `SessionResultsDue` per session per hour until its results are final."""
    hour = now.replace(minute=0, second=0, microsecond=0)
    for ref in scheduling.sessions_awaiting_results(now, after=RESULTS_AFTER, until=RESULTS_UNTIL):
        yield DueEvent(
            job=f"session-results:{ref.id}",
            slot=hour,
            event_type="SessionResultsDue",
            key=f"session:{ref.id}",
            payload={"session_id": ref.id},
        )


def analytics_due(now: dt.datetime):
    """One `AnalyticsDue` per race or sprint per two-hour slot in the first day after it ends."""
    slot = now.replace(hour=now.hour - now.hour % 2, minute=0, second=0, microsecond=0)
    for ref in scheduling.sessions_ended_between(
        now, after=ANALYTICS_AFTER, until=ANALYTICS_UNTIL, types=ANALYTICS_TYPES
    ):
        yield DueEvent(
            job=f"analytics:{ref.id}",
            slot=slot,
            event_type="AnalyticsDue",
            key=f"session:{ref.id}",
            payload={"session_id": ref.id},
        )


def on_analytics_due(event) -> None:
    ref = scheduling.session_ref(event.payload["session_id"])
    if ref is None or ref.round is None or ref.year < 2023:  # OpenF1 starts in 2023
        return
    summary = run_import(
        OpenF1Client(),
        years=[ref.year],
        round_number=ref.round,
        types=frozenset({ref.type}),
        force=False,
        dry_run=False,
    )
    run = summary.run
    if run.status == run.Status.FAILED:
        raise RuntimeError(f"OpenF1 import failed for session {ref.id}")  # retried by the outbox
    if run.errors:
        # Typically a driver that only appeared in practice (fix DriverNumberMap in the admin).
        # A retry cannot repair that, so it is reported but does not fail the event.
        log.warning(
            "OpenF1 import for session %s finished with %s problem(s)", ref.id, len(run.errors)
        )


def on_session_results_due(event) -> None:
    result = sync.sync_session_results(shared_client(), event.payload["session_id"])
    ref = scheduling.session_ref(event.payload["session_id"])
    # Standings follow the race. Retry through the outbox if the source lags behind.
    if result.available and ref and ref.type == "RACE" and ref.round is not None:
        sync.sync_standings(shared_client(), ref.year, ref.round)


def on_calendar_sync_due(event) -> None:
    today = timezone.localdate()
    year = scheduling.current_season_year(today) or today.year
    sync.sync_calendar(shared_client(), year)
    if today.month >= 11:  # next season's calendar appears towards the end of the year
        try:
            sync.sync_calendar(shared_client(), year + 1)
        except Exception:
            log.info("No calendar for %s yet", year + 1)


def on_results_corrections_due(event) -> None:
    latest = scheduling.latest_finished_round(timezone.now(), within=CORRECTIONS_WINDOW)
    if latest:
        sync.sync_round_after_race(shared_client(), *latest)


def register() -> None:
    subscribe("SessionResultsDue")(on_session_results_due)
    subscribe("CalendarSyncDue")(on_calendar_sync_due)
    subscribe("ResultsCorrectionsDue")(on_results_corrections_due)
    register_provider(results_due)
    subscribe("AnalyticsDue")(on_analytics_due)
    register_provider(analytics_due)

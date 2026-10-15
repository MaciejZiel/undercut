"""Event handlers that keep the frontend's page cache fresh. They only translate facts into tags."""

from __future__ import annotations

from apps.events.registry import subscribe

from . import tags
from .client import revalidate


def on_results_finalized(event) -> None:
    revalidate(tags.for_session(event.payload["session_id"], results_changed=True))


def on_standings_updated(event) -> None:
    revalidate(tags.for_standings(event.payload["year"]))


def on_analytics_imported(event) -> None:
    revalidate(tags.for_session(event.payload["session_id"], results_changed=False))


def on_history_imported(event) -> None:
    payload = event.payload
    revalidate(tags.for_history_import(payload.get("from_year"), payload.get("to_year")))


def register() -> None:
    subscribe("SessionResultsFinalized")(on_results_finalized)
    subscribe("StandingsUpdated")(on_standings_updated)
    subscribe("AnalyticsImported")(on_analytics_imported)
    subscribe("HistoryImported")(on_history_imported)

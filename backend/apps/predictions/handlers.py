"""Event handlers. Delivery is at-least-once, so all of them are "recompute", never "apply"."""

from __future__ import annotations

from apps.catalog import selectors as catalog
from apps.events.registry import subscribe

SESSION_RESULTS_FINALIZED = "SessionResultsFinalized"
PREDICTIONS_CLOSED = "PredictionsClosed"
RACE = "RACE"


def on_session_results_finalized(event) -> None:
    """Score a round when its race results are final (also after a correction).

    Other session types are ignored. Publishes PredictionsScored in the same transaction.
    """
    from . import services

    session = catalog.session_info(event.payload["session_id"])
    if session is None or session["type"] != RACE:
        return
    services.score_round_and_publish(session["round_id"])


def on_predictions_closed(event) -> None:
    """No-op placeholder that documents the lock moment.

    The lock is enforced on the server by comparing "now" with the qualifying start time on every
    write (services.is_locked), so nothing has to happen when this event arrives. The scheduler
    publishes it at that moment so other modules (for example e-mail reminders or cache
    revalidation of the now-visible picks) can react to it.
    """


def register_handlers() -> None:
    subscribe(SESSION_RESULTS_FINALIZED)(on_session_results_finalized)
    subscribe(PREDICTIONS_CLOSED)(on_predictions_closed)

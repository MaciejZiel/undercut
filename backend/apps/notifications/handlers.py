import logging

from apps.events.registry import subscribe

logger = logging.getLogger(__name__)


def handle_race_result(event) -> None:
    """Send the post-race e-mail (FR-505) to opted-in users.

    TODO: stub. The e-mail content (podium, favourites' results, prediction score, round link)
    comes in a later step. When implemented it must stay idempotent under at-least-once delivery
    (e.g. record a sent marker per user and round) and finish within 6 h of the result sync.
    Both event types land here: ``SessionResultsFinalized`` (key ``session:<id>``, payload
    ``session_id``, ``version``) and ``PredictionsScored`` (key ``round:<id>``, payload
    ``round_id``); the mail should go out once the predictions of the round are scored.
    """
    logger.debug("Race result e-mail not implemented yet (event %s)", event)


def register_handlers() -> None:
    for event_type in ("SessionResultsFinalized", "PredictionsScored"):
        subscribe(event_type)(handle_race_result)

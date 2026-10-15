"""Operator actions of the ingestion module (used by the admin and management commands)."""

from django.db import transaction

from apps.catalog import scheduling
from apps.events.publisher import publish

from .handlers import ANALYTICS_TYPES, OPENF1_FIRST_YEAR

PRACTICE_TYPES = frozenset({"FP1", "FP2", "FP3"})


class RoundNotFound(LookupError):
    pass


def request_round_resync(year: int, number: int, *, analytics: bool = True) -> dict[str, int]:
    """Queue a fresh sync of every session of a round: results, practice, standings, analytics.

    The work happens in the outbox worker, exactly like the scheduled run, and every handler is
    idempotent, so repeating this is harmless. Returns how many events were queued per type.
    """
    sessions = scheduling.round_sessions(year, number)
    if not sessions:
        raise RoundNotFound(f"No round {number} in {year}")
    queued = {"SessionResultsDue": 0, "AnalyticsDue": 0, "PracticeResultsDue": 0}
    with transaction.atomic():
        for ref in sessions:
            event = "PracticeResultsDue" if ref.type in PRACTICE_TYPES else "SessionResultsDue"
            if event == "PracticeResultsDue" and year < OPENF1_FIRST_YEAR:
                continue  # there is no source for practice results before 2023
            publish(event, key=f"session:{ref.id}", payload={"session_id": ref.id})
            queued[event] += 1
            if analytics and ref.type in ANALYTICS_TYPES and year >= OPENF1_FIRST_YEAR:
                publish("AnalyticsDue", key=f"session:{ref.id}", payload={"session_id": ref.id})
                queued["AnalyticsDue"] += 1
    return queued

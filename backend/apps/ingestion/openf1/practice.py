"""Practice results from OpenF1's `session_result` (FR-204).

Jolpica has practice results only in its database dump (2025 on) and no practice endpoint in its
API, so OpenF1 fills the gap: the same data from 2023 and within minutes of the session ending.
Rows hold position, laps and best lap; practice has no points or grid.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from django.db import transaction

from apps.catalog import scheduling
from apps.catalog import services as catalog
from apps.events.publisher import publish

from . import matching
from . import schemas as s
from .client import OpenF1Client
from .importer import EVENT_TYPE

log = logging.getLogger(__name__)

PRACTICE_TYPES = frozenset({"FP1", "FP2", "FP3"})
FINAL_AFTER = dt.timedelta(minutes=30)  # the classification is settled this long after the end


def to_ms(seconds) -> int | None:
    """A lap time in seconds (float) to milliseconds; anything else is no time."""
    if isinstance(seconds, bool) or not isinstance(seconds, int | float) or seconds <= 0:
        return None
    return round(seconds * 1000)


@dataclass
class PracticeOutcome:
    session_id: int
    rows: int = 0
    created: int = 0
    updated: int = 0
    final: bool = False
    problems: list[str] = field(default_factory=list)


def build_rows(
    year: int,
    results: list[dict],
    drivers: list[s.Driver],
    mapping: dict[int, int],
) -> tuple[list[catalog.PracticeData], list[str]]:
    """Practice rows with catalog ids, plus a note for every driver that could not be placed."""
    teams = {d.driver_number: d.team_name for d in drivers if d.driver_number is not None}
    rows: list[catalog.PracticeData] = []
    problems: list[str] = []
    for item in results:
        number = item.get("driver_number")
        if item.get("dns"):
            continue
        if not isinstance(number, int):
            problems.append(f"row without a car number: {item}")
            continue
        driver_id = mapping.get(number)
        if driver_id is None:
            problems.append(f"car {number}: no catalog driver")
            continue
        constructor_id = catalog.resolve_constructor_id(driver_id, year, teams.get(number))
        if constructor_id is None:
            problems.append(f"car {number}: team unknown ({teams.get(number)})")
            continue
        position = item.get("position")
        rows.append(
            catalog.PracticeData(
                driver_id=driver_id,
                constructor_id=constructor_id,
                position=position if isinstance(position, int) and position >= 1 else None,
                laps=item.get("number_of_laps")
                if isinstance(item.get("number_of_laps"), int)
                else None,
                best_lap_ms=to_ms(item.get("duration")),
            )
        )
    return rows, problems


def import_practice_session(
    client: OpenF1Client, ms: matching.MatchedSession, *, now: dt.datetime | None = None
) -> PracticeOutcome:
    """Fetch and store the classification of one practice session. Idempotent."""
    now = now or dt.datetime.now(dt.UTC)
    outcome = PracticeOutcome(session_id=ms.session_id)
    results = client.get("session_result", {"session_key": ms.session_key})
    if not results:
        return outcome  # not published yet: the next poll tries again
    drivers = s.Driver.parse_all(client.get("drivers", {"session_key": ms.session_key}))
    with transaction.atomic():
        resolution = matching.resolve_drivers(ms.year, drivers)
        rows, problems = build_rows(ms.year, results, drivers, resolution.mapping)
        outcome.problems = problems + [str(item["error"]) for item in resolution.unmatched]
        counts = catalog.upsert_practice_results(ms.session_id, rows)
        outcome.rows, outcome.created, outcome.updated = len(rows), counts.created, counts.updated
        ended = ms.end_utc is not None and ms.end_utc + FINAL_AFTER <= now
        became_final = False
        if rows and ended:
            outcome.final = True
            became_final = scheduling.set_session_status(ms.session_id, "results_final")
        if counts.created or counts.updated or became_final:
            publish(
                EVENT_TYPE, key=f"session:{ms.session_id}", payload={"session_id": ms.session_id}
            )
    for line in outcome.problems:
        log.warning("Practice session %s: %s", ms.session_id, line)
    return outcome


def import_practice(
    client: OpenF1Client,
    *,
    years: list[int],
    only_missing: bool = True,
    session_id: int | None = None,
    now: dt.datetime | None = None,
) -> list[PracticeOutcome]:
    """Backfill practice results for whole seasons (2023 on). Sessions that already have
    results are skipped when `only_missing` (the dump already delivered them)."""
    now = now or dt.datetime.now(dt.UTC)
    outcomes: list[PracticeOutcome] = []
    for year in years:
        meetings = s.Meeting.parse_all(client.get("meetings", {"year": year}))
        sessions = s.Session.parse_all(client.get("sessions", {"year": year}))
        if not meetings or not sessions:
            continue
        with transaction.atomic():
            match = matching.match_year(year, meetings, sessions)
        for ms in match.sessions:
            if ms.type not in PRACTICE_TYPES or ms.end_utc is None or ms.end_utc > now:
                continue
            if session_id is not None and ms.session_id != session_id:
                continue
            if only_missing and scheduling.has_results(ms.session_id):
                continue
            outcomes.append(import_practice_session(client, ms, now=now))
    return outcomes

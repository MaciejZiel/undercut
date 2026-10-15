"""Ongoing synchronisation from the Jolpica API: calendar, session results and standings.

Everything here is idempotent. Results are re-fetched after the race (penalties and
disqualifications arrive late), unchanged data writes nothing, and rows a human corrected
in the admin (`manual_override`) are never overwritten.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.catalog import references, scheduling
from apps.catalog import services as catalog
from apps.events.publisher import publish
from apps.ingestion.models import SyncRun
from apps.standings import services as standings

from . import api_mapper
from .client import JolpicaClient

log = logging.getLogger(__name__)

SOURCE = "jolpica-api"
RESULTS_FINALIZED = "SessionResultsFinalized"
STANDINGS_UPDATED = "StandingsUpdated"

Totals = dict[str, catalog.Counts]


def _start(job: str, scope: dict) -> SyncRun:
    return SyncRun.objects.create(source=SOURCE, job=job, scope=scope)


def _close(run: SyncRun, totals: Totals, errors: list[dict]) -> SyncRun:
    run.created = sum(c.created for c in totals.values())
    run.updated = sum(c.updated for c in totals.values())
    run.skipped = sum(c.skipped_manual for c in totals.values())
    run.errors = errors
    run.status = SyncRun.Status.PARTIAL if errors else SyncRun.Status.SUCCESS
    run.finished_at = timezone.now()
    run.save()
    return run


def _fail(run: SyncRun, exc: Exception) -> None:
    run.status = SyncRun.Status.FAILED
    run.errors = [*run.errors, {"error": f"{type(exc).__name__}: {exc}"[:500]}]
    run.finished_at = timezone.now()
    run.save()


# --------------------------------------------------------------------------- calendar


def sync_calendar(client: JolpicaClient, year: int) -> SyncRun:
    """Rounds and session times of one season. Never deletes a round."""
    run = _start("calendar", {"year": year})
    totals: Totals = defaultdict(catalog.Counts)
    errors: list[dict] = []
    try:
        races = api_mapper.parse_schedule(client.schedule(year))
        with transaction.atomic():
            totals["season"].record(catalog.upsert_season(catalog.SeasonData(year=year)))
            for race in races:
                totals["circuit"].record(catalog.upsert_circuit(race.circuit))
                outcome = catalog.upsert_round(race.round)
                totals["round"].record(outcome)
                for session in race.sessions:
                    totals["session"].record(catalog.upsert_session(outcome.id, session))
            # An empty answer is an outage, not "every race was cancelled".
            if races:
                gone = scheduling.mark_missing_rounds_cancelled(
                    year, {r.round.round for r in races if r.round.round is not None}
                )
                if gone:
                    errors.append(
                        {"warning": "rounds missing from source, marked cancelled", "rounds": gone}
                    )
    except Exception as exc:
        _fail(run, exc)
        raise
    return _close(run, totals, errors)


# --------------------------------------------------------------------------- results


@dataclass(frozen=True)
class ResultsSync:
    session_id: int
    available: bool  # the source had results for this session
    changed: bool  # rows were created or updated, or the session became final


def _publish_finalized(session_id: int, now: dt.datetime) -> None:
    publish(
        RESULTS_FINALIZED,
        key=f"session:{session_id}",
        payload={"session_id": session_id, "version": int(now.timestamp())},
    )


def sync_session_results(
    client: JolpicaClient, session_id: int, *, now: dt.datetime | None = None
) -> ResultsSync:
    now = now or timezone.now()
    ref = scheduling.session_ref(session_id)
    if ref is None or ref.round is None or ref.type not in scheduling.SYNCED_TYPES:
        return ResultsSync(session_id, available=False, changed=False)

    run = _start(
        "session-results", {"session_id": session_id, "year": ref.year, "round": ref.round}
    )
    totals: Totals = defaultdict(catalog.Counts)
    errors: list[dict] = []
    try:
        if ref.type == "RACE":
            parsed = api_mapper.parse_race_results(client.results(ref.year, ref.round))
        elif ref.type == "SPRINT":
            parsed = api_mapper.parse_race_results(
                client.sprint(ref.year, ref.round), "SprintResults"
            )
        else:
            parsed = api_mapper.parse_qualifying(client.qualifying(ref.year, ref.round))

        if not parsed.rows:  # not published yet; the next poll tries again
            _close(run, totals, errors)
            return ResultsSync(session_id, available=False, changed=False)

        with transaction.atomic():
            for driver in parsed.drivers.values():
                totals["driver"].record(catalog.upsert_driver(driver))
            for constructor in parsed.constructors.values():
                totals["constructor"].record(catalog.upsert_constructor(constructor))
            for item in api_mapper.race_constructors_by_year(parsed, ref.year):
                totals["constructor_season"].record(catalog.upsert_constructor_season(item))
            if ref.type == "Q":
                counts = catalog.upsert_qualifying(session_id, parsed.rows)
                totals["qualifying"].add(counts)
            else:
                counts = catalog.upsert_results(session_id, parsed.rows)
                totals["result"].add(counts)
            became_final = scheduling.set_session_status(session_id, "results_final")
            changed = bool(counts.created or counts.updated) or became_final
            if changed:
                _publish_finalized(session_id, now)
        _close(run, totals, errors)
    except Exception as exc:
        _fail(run, exc)
        raise
    return ResultsSync(session_id, available=True, changed=changed)


# --------------------------------------------------------------------------- standings


def sync_standings(client: JolpicaClient, year: int, number: int) -> SyncRun:
    """Championship tables after one round, as published (never recomputed)."""
    run = _start("standings", {"year": year, "round": number})
    totals: Totals = defaultdict(catalog.Counts)
    errors: list[dict] = []
    try:
        season_ids = references.season_ids_by_year()
        season_id = season_ids.get(year)
        if season_id is None:
            raise LookupError(f"Season {year} is not in the catalog")
        drivers, constructors = api_mapper.parse_standings(client.driver_standings(year, number))
        _, teams = api_mapper.parse_standings(client.constructor_standings(year, number))
        constructors = teams or constructors
        driver_podiums, team_podiums = scheduling.podium_counts(season_id, number)

        with transaction.atomic():
            for line in drivers:
                if line.driver:
                    catalog.upsert_driver(line.driver)
            for line in constructors:
                if line.constructor:
                    catalog.upsert_constructor(line.constructor)
            driver_ids = references.driver_ids_by_jolpica_id()
            constructor_ids = references.constructor_ids_by_jolpica_id()

            def rows(lines, ids, podiums, key):
                return [
                    {
                        key: ids[line.jolpica_id],
                        "position": line.position,
                        "position_text": line.position_text,
                        "points": line.points,
                        "wins": line.wins,
                        "podiums": podiums.get(line.jolpica_id, 0),
                    }
                    for line in lines
                    if line.jolpica_id in ids
                ]

            changed = 0
            for name, replace, lines, ids, podiums, key in (
                (
                    "driver_standing",
                    standings.replace_driver_standings,
                    drivers,
                    driver_ids,
                    driver_podiums,
                    "driver_id",
                ),
                (
                    "constructor_standing",
                    standings.replace_constructor_standings,
                    constructors,
                    constructor_ids,
                    team_podiums,
                    "constructor_id",
                ),
            ):
                if not lines:
                    continue
                result = replace(season_id, number, rows(lines, ids, podiums, key))
                totals[name].created += result["created"]
                totals[name].updated += result["updated"]
                changed += result["created"] + result["updated"] + result["deleted"]
            if changed:
                publish(
                    STANDINGS_UPDATED,
                    key=f"season:{year}",
                    payload={"season_id": season_id, "year": year, "after_round": number},
                )
    except Exception as exc:
        _fail(run, exc)
        raise
    return _close(run, totals, errors)


def sync_round_after_race(client: JolpicaClient, year: int, number: int) -> None:
    """Corrections: re-read every synced session of a round, then its standings."""
    for ref in scheduling.round_sessions(year, number):
        if ref.type in scheduling.SYNCED_TYPES:
            sync_session_results(client, ref.id)
    sync_standings(client, year, number)

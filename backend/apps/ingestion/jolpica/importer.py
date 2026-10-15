"""Orchestrates the history import: dump to mapper to catalog services, one round at a time."""

from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.catalog import services as catalog
from apps.events.publisher import publish
from apps.ingestion.models import SyncRun

from . import mapper
from .dump import Dump, open_dump, read_dump

log = logging.getLogger(__name__)

SOURCE = "jolpica-dump"
JOB = "import_history"
EVENT_TYPE = "HistoryImported"

Report = Callable[[str], None]


class _DryRunRollback(Exception):
    pass


def _tally(totals: dict[str, catalog.Counts], name: str, outcome: catalog.Outcome) -> None:
    totals[name].record(outcome)


def _import(
    dump: Dump,
    from_year: int | None,
    to_year: int | None,
    today: dt.date,
    totals: dict[str, catalog.Counts],
    errors: list[dict],
    report: Report,
) -> int:
    years = mapper.season_years(dump, from_year, to_year)
    rounds = mapper.rounds_in_range(dump, from_year, to_year)

    with transaction.atomic():  # reference data is one unit
        for season in mapper.map_seasons(dump, from_year, to_year):
            _tally(totals, "season", catalog.upsert_season(season))
        for circuit in mapper.map_circuits(dump, rounds):
            _tally(totals, "circuit", catalog.upsert_circuit(circuit))
        for driver in mapper.map_drivers(dump, years, rounds):
            _tally(totals, "driver", catalog.upsert_driver(driver))
        for constructor in mapper.map_constructors(dump, years):
            _tally(totals, "constructor", catalog.upsert_constructor(constructor))
        for item in mapper.map_constructor_seasons(dump, years):
            _tally(totals, "constructor_season", catalog.upsert_constructor_season(item))
    report(f"Reference data done ({len(rounds)} rounds to import).")

    done = 0
    for row, bundle in mapper.iter_rounds(dump, rounds, years, today=today):
        label = f"{years[row.season_id]} {row.name}"
        try:
            outcome = catalog.import_round(bundle)  # atomic: one round, one transaction
        except Exception as exc:
            log.exception("Round failed: %s", label)
            errors.append({"round": label, "error": f"{type(exc).__name__}: {exc}"[:500]})
            continue
        _tally(totals, "round", outcome.round)
        totals["session"].add(outcome.sessions)
        totals["result"].add(outcome.results)
        totals["qualifying"].add(outcome.qualifying)
        done += 1
        if done % 100 == 0:
            report(f"  {done}/{len(rounds)} rounds")
    return done


def run_import(
    path: Path,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    dry_run: bool = False,
    today: dt.date | None = None,
    report: Report = lambda _msg: None,
) -> tuple[SyncRun, dict[str, catalog.Counts]]:
    today = today or timezone.localdate()
    run = SyncRun.objects.create(
        source=SOURCE,
        job=JOB,
        scope={
            "dump": path.name,
            "from_year": from_year,
            "to_year": to_year,
            "dry_run": dry_run,
        },
    )
    totals: dict[str, catalog.Counts] = defaultdict(catalog.Counts)
    errors: list[dict] = []
    imported = 0
    try:
        with open_dump(path) as directory:
            report("Reading dump...")
            dump = read_dump(directory)
        try:
            with transaction.atomic():
                imported = _import(dump, from_year, to_year, today, totals, errors, report)
                if dry_run:
                    raise _DryRunRollback
                run.status = SyncRun.Status.PARTIAL if errors else SyncRun.Status.SUCCESS
                _finish(run, totals, errors)
                if imported:
                    publish(
                        EVENT_TYPE,
                        key="history",
                        payload={
                            "sync_run_id": run.pk,
                            "from_year": from_year,
                            "to_year": to_year,
                            "rounds": imported,
                        },
                    )
        except _DryRunRollback:
            pass
    except Exception as exc:
        log.exception("History import failed")
        errors.append({"round": None, "error": f"{type(exc).__name__}: {exc}"[:500]})
        run.status = SyncRun.Status.FAILED
        _finish(run, totals, errors)
        raise
    if dry_run:
        run.status = SyncRun.Status.PARTIAL if errors else SyncRun.Status.SUCCESS
        _finish(run, totals, errors)
    return run, totals


def _finish(run: SyncRun, totals: dict[str, catalog.Counts], errors: list[dict]) -> None:
    run.created = sum(c.created for c in totals.values())
    run.updated = sum(c.updated for c in totals.values())
    run.skipped = sum(c.skipped_manual for c in totals.values())
    run.errors = errors
    run.finished_at = timezone.now()
    run.save()

"""OpenF1 analytics import: one session = one transaction.

Flow per year: fetch meetings and sessions, match them to the catalog (storing the keys), then for
each finished session fetch its data, resolve drivers, map the rows and call the idempotent
writers of `apps.analytics.services`. Progress is stored in `SyncRun.scope["done"]`, in the same
transaction as the data, so an interrupted backfill resumes where it stopped and a session that
is done is skipped unless `force` is set.
"""

from __future__ import annotations

import copy
import datetime as dt
import logging
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from apps.analytics import services as analytics
from apps.events.publisher import publish
from apps.ingestion.models import SyncRun

from . import mapper, matching
from . import schemas as s
from .client import OpenF1Client, ResponseTooLarge

log = logging.getLogger(__name__)

SOURCE = "openf1"
JOB = "import_openf1"
EVENT_TYPE = "AnalyticsImported"

# Position and intervals are large and only meaningful for races.
RACE_LIKE = frozenset({"RACE", "SPRINT"})
FINISHED_STATUSES = frozenset({"finished", "results_final"})

WINDOW = dt.timedelta(minutes=60)
MIN_WINDOW = dt.timedelta(minutes=2)
POSITION_LEAD = dt.timedelta(minutes=90)  # position is event driven: grid order is sent early
INTERVAL_LEAD = dt.timedelta(minutes=5)
TAIL = dt.timedelta(minutes=10)
MAX_CONSECUTIVE_FAILURES = 3

Report = Callable[[str], None]


class _DryRunRollback(Exception):
    pass


class _Abort(Exception):
    pass


@dataclass
class ImportSummary:
    run: SyncRun
    dry_run: bool = False
    rows: Counter = field(default_factory=Counter)  # table -> rows written
    unmapped_rows: int = 0
    imported: list[str] = field(default_factory=list)
    skipped: dict[str, list[str]] = field(default_factory=dict)  # reason -> sessions
    notes: list[str] = field(default_factory=list)
    requests: int = 0
    by_endpoint: Counter = field(default_factory=Counter)

    def skip(self, reason: str, label: str) -> None:
        self.skipped.setdefault(reason, []).append(label)


@dataclass(frozen=True)
class SessionData:
    drivers: list[s.Driver]
    laps: list[s.Lap]
    stints: list[s.Stint]
    pits: list[s.Pit]
    race_control: list[s.RaceControl]
    weather: list[s.Weather]
    positions: list[s.Position]
    intervals: list[s.Interval]


def _fmt(moment: dt.datetime) -> str:
    return moment.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _fetch_window(
    client: OpenF1Client, endpoint: str, key: int, start: dt.datetime, stop: dt.datetime
) -> list[dict]:
    params = {"session_key": key, "date>=": _fmt(start), "date<": _fmt(stop)}
    try:
        return client.get(endpoint, params)
    except ResponseTooLarge:
        if stop - start <= MIN_WINDOW:
            raise
        half = dt.timedelta(seconds=int((stop - start).total_seconds() // 2))
        mid = start + half
        return _fetch_window(client, endpoint, key, start, mid) + _fetch_window(
            client, endpoint, key, mid, stop
        )


def fetch_windowed(
    client: OpenF1Client,
    endpoint: str,
    key: int,
    start: dt.datetime | None,
    end: dt.datetime | None,
) -> list[dict]:
    """Large time series in half-open windows, so no single request is big (window halves again
    if the response cap is hit). Without a known time range the whole session is requested."""
    if start is None or end is None:
        return client.get(endpoint, {"session_key": key})
    rows: list[dict] = []
    cursor = start
    while cursor < end:
        stop = min(cursor + WINDOW, end)
        rows.extend(_fetch_window(client, endpoint, key, cursor, stop))
        cursor = stop
    return rows


def fetch_session(client: OpenF1Client, ms: matching.MatchedSession) -> SessionData:
    key = ms.session_key
    by_session = {"session_key": key}
    positions: list[dict] = []
    intervals: list[dict] = []
    drivers = client.get("drivers", by_session)
    laps = client.get("laps", by_session)
    stints = client.get("stints", by_session)
    pits = client.get("pit", by_session)
    race_control = client.get("race_control", by_session)
    weather = client.get("weather", by_session)
    if ms.type in RACE_LIKE:
        start, end = ms.start_utc, ms.end_utc
        positions = fetch_windowed(
            client,
            "position",
            key,
            start - POSITION_LEAD if start else None,
            end + TAIL if end else None,
        )
        intervals = fetch_windowed(
            client,
            "intervals",
            key,
            start - INTERVAL_LEAD if start else None,
            end + TAIL if end else None,
        )
    return SessionData(
        drivers=s.Driver.parse_all(drivers),
        laps=s.Lap.parse_all(laps),
        stints=s.Stint.parse_all(stints),
        pits=s.Pit.parse_all(pits),
        race_control=s.RaceControl.parse_all(race_control),
        weather=s.Weather.parse_all(weather),
        positions=s.Position.parse_all(positions),
        intervals=s.Interval.parse_all(intervals),
    )


def _dedupe(rows: Iterable, key: Callable) -> list:
    """The writers use INSERT .. ON CONFLICT, which rejects a repeated key inside one batch."""
    return list({key(r): r for r in rows}.values())


def _mapped(rows: Iterable, convert: Callable, summary: ImportSummary) -> list:
    out = []
    for row in rows:
        mapped = convert(row)
        if mapped is None:
            summary.unmapped_rows += 1
        else:
            out.append(mapped)
    return out


def write_session(
    ms: matching.MatchedSession,
    data: SessionData,
    mapping: dict[int, int],
    summary: ImportSummary,
) -> Counter:
    sid = ms.session_id
    laps = _dedupe(
        _mapped(data.laps, lambda r: mapper.map_lap(r, sid, mapping), summary),
        lambda r: (r.driver_id, r.lap_number),
    )
    stints = _dedupe(
        _mapped(data.stints, lambda r: mapper.map_stint(r, sid, mapping), summary),
        lambda r: (r.driver_id, r.stint_number),
    )
    pits = _dedupe(
        _mapped(data.pits, lambda r: mapper.map_pit(r, sid, mapping), summary),
        lambda r: (r.driver_id, r.date),
    )
    positions = _dedupe(
        _mapped(data.positions, lambda r: mapper.map_position(r, sid, mapping), summary),
        lambda r: (r.driver_id, r.ts),
    )
    intervals = _dedupe(
        _mapped(data.intervals, lambda r: mapper.map_interval(r, sid, mapping), summary),
        lambda r: (r.driver_id, r.ts),
    )
    weather = _dedupe(
        _mapped(data.weather, lambda r: mapper.map_weather(r, sid), summary), lambda r: r.ts
    )
    control = _mapped(
        data.race_control, lambda r: mapper.map_race_control(r, sid, mapping), summary
    )
    written = Counter()
    written["lap"] = analytics.upsert_laps(laps)
    written["stint"] = analytics.upsert_stints(stints)
    written["pit_stop"] = analytics.upsert_pit_stops(pits)
    written["position"] = analytics.upsert_positions(positions)
    written["interval"] = analytics.upsert_intervals(intervals)
    written["weather"] = analytics.upsert_weather(weather)
    written["race_control_new"] = analytics.insert_race_control(control)
    return written


def _label(ms: matching.MatchedSession) -> str:
    return f"{ms.year} R{ms.round_number or '-'} {ms.type} (key {ms.session_key})"


def previously_done() -> set[int]:
    """Session keys that an earlier, committed run imported completely."""
    done: set[int] = set()
    for scope in SyncRun.objects.filter(source=SOURCE, job=JOB).values_list("scope", flat=True):
        if isinstance(scope, dict) and not scope.get("dry_run"):
            done.update(int(k) for k in scope.get("done", {}))
    return done


def is_finished(ms: matching.MatchedSession, now: dt.datetime) -> bool:
    if ms.status in FINISHED_STATUSES:
        return True
    return ms.end_utc is not None and ms.end_utc <= now


class _Importer:
    def __init__(
        self,
        client: OpenF1Client,
        run: SyncRun,
        summary: ImportSummary,
        *,
        force: bool,
        dry_run: bool,
        now: dt.datetime,
        report: Report,
    ):
        self.client = client
        self.run = run
        self.summary = summary
        self.force = force
        self.dry_run = dry_run
        self.now = now
        self.report = report
        self.errors: list[dict] = []
        self._seen: set[str] = set()
        self.done = set() if force else previously_done()
        self.failures = 0

    def error(self, item: dict) -> None:
        fingerprint = repr(sorted(item.items()))
        if fingerprint not in self._seen:
            self._seen.add(fingerprint)
            self.errors.append(item)

    def sync_counters(self) -> None:
        self.summary.requests = self.client.requests
        self.summary.by_endpoint = Counter(self.client.by_endpoint)

    # ---- selection

    def sessions_for_year(
        self,
        year: int,
        *,
        round_number: int | None,
        session_key: int | None,
        types: frozenset[str] | None,
    ) -> list[matching.MatchedSession]:
        meetings = s.Meeting.parse_all(self.client.get("meetings", {"year": year}))
        sessions = s.Session.parse_all(self.client.get("sessions", {"year": year}))
        if not meetings or not sessions:
            self.summary.notes.append(f"{year}: OpenF1 has no meetings/sessions")
            return []
        only = None
        if session_key is not None:
            found = [x for x in sessions if x.session_key == session_key]
            only = {x.meeting_key for x in found if x.meeting_key is not None}
        with transaction.atomic():
            match = matching.match_year(year, meetings, sessions, meeting_keys=only)
        for item in match.errors:
            self.error(item)
        self.summary.notes.extend(match.notes)
        picked = match.sessions
        if session_key is not None:
            picked = [m for m in picked if m.session_key == session_key]
        if round_number is not None:
            picked = [m for m in picked if m.round_number == round_number]
        if types is not None:
            picked = [m for m in picked if m.type in types]
        return sorted(picked, key=lambda m: (m.start_utc or self.now, m.session_key))

    # ---- one session

    def import_session(self, ms: matching.MatchedSession) -> None:
        label = _label(ms)
        if ms.session_key in self.done:
            self.summary.skip("already imported", label)
            return
        if not is_finished(ms, self.now):
            self.summary.skip("not finished", label)
            return
        try:
            data = fetch_session(self.client, ms)
            if not data.drivers:
                self.error(
                    {
                        "type": "no_data",
                        "session_key": ms.session_key,
                        "session": label,
                        "error": "OpenF1 returned no drivers for a finished session",
                    }
                )
                self.summary.skip("no data", label)
                return
            written = self._write(ms, data)
        except Exception as exc:  # one bad session must not stop a backfill
            log.exception("Session failed: %s", label)
            self.error(
                {
                    "type": "session_failed",
                    "session_key": ms.session_key,
                    "session": label,
                    "error": f"{type(exc).__name__}: {exc}"[:500],
                }
            )
            self.failures += 1
            if self.failures >= MAX_CONSECUTIVE_FAILURES:
                raise _Abort(f"{self.failures} sessions failed in a row") from exc
            return
        self.failures = 0
        self.summary.rows.update(written)
        self.summary.imported.append(label)
        self.report(f"  {label}: " + ", ".join(f"{k}={v}" for k, v in written.items()))

    def _write(self, ms: matching.MatchedSession, data: SessionData) -> Counter:
        previous_scope = copy.deepcopy(self.run.scope)
        try:
            with transaction.atomic():
                resolution = matching.resolve_drivers(ms.year, data.drivers)
                for item in resolution.unmatched:
                    self.error(item)
                written = write_session(ms, data, resolution.mapping, self.summary)
                if not self.dry_run:
                    self.run.scope.setdefault("done", {})[str(ms.session_key)] = {
                        "session_id": ms.session_id,
                        "at": timezone.now().isoformat(),
                        "rows": dict(written),
                    }
                    self.run.save(update_fields=["scope"])
                publish(
                    EVENT_TYPE,
                    key=f"session:{ms.session_id}",
                    payload={"session_id": ms.session_id},
                )
        except Exception:
            self.run.scope = previous_scope
            raise
        return written


def run_import(
    client: OpenF1Client,
    *,
    years: list[int] | None = None,
    round_number: int | None = None,
    session_key: int | None = None,
    types: frozenset[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
    now: dt.datetime | None = None,
    report: Report = lambda _msg: None,
) -> ImportSummary:
    now = now or timezone.now()
    run = SyncRun.objects.create(
        source=SOURCE,
        job=JOB,
        scope={
            "years": years,
            "round": round_number,
            "session_key": session_key,
            "types": sorted(types) if types else None,
            "force": force,
            "dry_run": dry_run,
            "done": {},
        },
    )
    summary = ImportSummary(run=run, dry_run=dry_run)
    imp = _Importer(client, run, summary, force=force, dry_run=dry_run, now=now, report=report)
    status = SyncRun.Status.SUCCESS
    try:
        if dry_run:
            try:
                with transaction.atomic():  # everything, then roll it all back
                    _execute(imp, years, round_number, session_key, types)
                    raise _DryRunRollback
            except _DryRunRollback:
                pass
        else:
            _execute(imp, years, round_number, session_key, types)
    except _Abort as exc:
        imp.error({"type": "aborted", "error": str(exc)})
        status = SyncRun.Status.FAILED
    except KeyboardInterrupt:
        imp.error({"type": "interrupted", "error": "stopped by user; rerun to resume"})
        _finish(imp, SyncRun.Status.PARTIAL)
        raise
    except Exception as exc:
        log.exception("OpenF1 import failed")
        imp.error({"type": "failed", "error": f"{type(exc).__name__}: {exc}"[:500]})
        _finish(imp, SyncRun.Status.FAILED)
        raise
    if status == SyncRun.Status.SUCCESS and imp.errors:
        status = SyncRun.Status.PARTIAL
    _finish(imp, status)
    return summary


def _execute(
    imp: _Importer,
    years: list[int] | None,
    round_number: int | None,
    session_key: int | None,
    types: frozenset[str] | None,
) -> None:
    if session_key is not None:
        rows = imp.client.get("sessions", {"session_key": session_key})
        found = s.Session.parse_all(rows)
        if not found or found[0].year is None:
            imp.error(
                {
                    "type": "unknown_session",
                    "session_key": session_key,
                    "error": "OpenF1 does not know this session key",
                }
            )
            return
        years = [found[0].year]
    for year in years or []:
        imp.report(f"{year}: matching meetings and sessions")
        sessions = imp.sessions_for_year(
            year, round_number=round_number, session_key=session_key, types=types
        )
        imp.report(f"{year}: {len(sessions)} session(s) selected")
        for ms in sessions:
            imp.import_session(ms)
            imp.sync_counters()


def _finish(imp: _Importer, status: str) -> None:
    run, summary = imp.run, imp.summary
    imp.sync_counters()
    run.status = status
    run.created = sum(summary.rows.values())  # rows written; the writers do not split new/updated
    run.updated = 0
    run.skipped = sum(len(v) for v in summary.skipped.values())
    run.errors = imp.errors
    run.scope["requests"] = summary.requests
    run.scope["rows"] = dict(summary.rows)
    run.finished_at = timezone.now()
    run.save()

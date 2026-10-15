"""Maps Jolpica dump rows onto the catalog service inputs.

Pure functions: no database access, no models. The dump is a normalised relational export, so the
mapper does the joins (entry -> round entry -> team driver) and the Q1/Q2/Q3 merge.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from apps.catalog.services import (
    CircuitData,
    ConstructorData,
    ConstructorSeasonData,
    DriverData,
    QualifyingData,
    ResultData,
    RoundBundle,
    RoundData,
    SeasonData,
    SessionBundle,
    SessionData,
)

from .dump import Dump, DumpError, RoundRow, SessionEntryRow, SessionRow

# Dump session code -> catalog Session.Type value.
SESSION_TYPES = {
    "R": "RACE",
    "SR": "SPRINT",
    "FP1": "FP1",
    "FP2": "FP2",
    "FP3": "FP3",
    "Q1": "Q",
    "Q2": "Q",
    "Q3": "Q",
    "QB": "Q",
    "QO": "Q",
    "QA": "Q",
    "SQ1": "SQ",
    "SQ2": "SQ",
    "SQ3": "SQ",
}

# sessionentry.status codes that are not a plain retirement.
STATUS_DISQUALIFIED = "20"
STATUS_WITHDREW = {"30", "40"}
STATUS_NOT_CLASSIFIED = "1"

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")
_INTERVAL = re.compile(r"^(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)$")


def parse_interval_ms(text: str) -> int | None:
    """'02:13:23.6', '00:01:16.29', '1:32.608' or '24.036' -> milliseconds."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        parts = [Decimal(p) for p in text.split(":")]
    except InvalidOperation:
        return None
    if not 1 <= len(parts) <= 3:
        return None
    seconds = Decimal(0)
    for part in parts:
        seconds = seconds * 60 + part
    return int((seconds * 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def parse_points(text: str) -> Decimal:
    try:
        return max(Decimal((text or "0").strip() or "0"), Decimal(0))
    except InvalidOperation:
        return Decimal(0)


def normalise_color(value: str) -> str | None:
    match = _HEX.match((value or "").strip())
    return f"#{match.group(1).lower()}" if match else None


def _date(value: str) -> dt.date:
    return dt.date.fromisoformat(value[:10])


def _start_utc(value: str) -> dt.datetime | None:
    """Old sessions carry a date at 00:00 UTC, which is "unknown", not a start time."""
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    parsed = parsed.astimezone(dt.UTC)
    return None if parsed.time() == dt.time(0, 0) else parsed


# --------------------------------------------------------------------------- reference data


def rounds_in_range(dump: Dump, from_year: int | None, to_year: int | None) -> list[RoundRow]:
    years = {s.id: s.year for s in dump.seasons}
    keep = []
    for row in dump.rounds:
        year = years.get(row.season_id)
        if year is None:
            continue
        if (from_year is not None and year < from_year) or (to_year is not None and year > to_year):
            continue
        keep.append(row)
    return keep


def season_years(dump: Dump, from_year: int | None, to_year: int | None) -> dict[int, int]:
    return {
        s.id: s.year
        for s in dump.seasons
        if (from_year is None or s.year >= from_year) and (to_year is None or s.year <= to_year)
    }


def map_seasons(dump: Dump, from_year: int | None, to_year: int | None) -> list[SeasonData]:
    return [SeasonData(year=y) for y in sorted(season_years(dump, from_year, to_year).values())]


def map_circuits(dump: Dump, rounds: Iterable[RoundRow]) -> list[CircuitData]:
    rounds = list(rounds)
    zones: dict[int, Counter] = {}
    for r in rounds:
        for s in dump.sessions_by_round.get(r.id, []):
            if s.timezone:
                zones.setdefault(r.circuit_id, Counter())[s.timezone] += 1
    out = []
    for circuit_id in sorted({r.circuit_id for r in rounds}):
        c = dump.circuits[circuit_id]
        zone = zones[circuit_id].most_common(1)[0][0] if circuit_id in zones else ""
        out.append(
            CircuitData(
                jolpica_id=c.reference,
                name=c.name,
                locality=c.locality,
                country=c.country,
                lat=c.latitude,
                lng=c.longitude,
                timezone=zone,
            )
        )
    return out


def _team_drivers_in(dump: Dump, years: dict[int, int]):
    return [td for td in dump.team_drivers.values() if td.season_id in years]


def map_drivers(dump: Dump, years: dict[int, int], rounds: Iterable[RoundRow]) -> list[DriverData]:
    ids = {td.driver_id for td in _team_drivers_in(dump, years)}
    out = []
    for driver_id in sorted(ids):
        d = dump.drivers[driver_id]
        try:
            dob = dt.date.fromisoformat(d.date_of_birth) if d.date_of_birth else None
        except ValueError:
            dob = None
        out.append(
            DriverData(
                jolpica_id=d.reference,
                given_name=d.forename,
                family_name=d.surname,
                code=d.abbreviation[:3],
                permanent_number=d.permanent_car_number,
                dob=dob,
                nationality=d.nationality,
            )
        )
    return out


def map_constructors(dump: Dump, years: dict[int, int]) -> list[ConstructorData]:
    ids = {td.team_id for td in _team_drivers_in(dump, years)}
    return [
        ConstructorData(
            jolpica_id=dump.teams[t].reference,
            name=dump.teams[t].name,
            nationality=dump.teams[t].nationality,
        )
        for t in sorted(ids)
    ]


def map_constructor_seasons(dump: Dump, years: dict[int, int]) -> list[ConstructorSeasonData]:
    pairs = {(td.team_id, td.season_id) for td in _team_drivers_in(dump, years)}
    return [
        ConstructorSeasonData(
            constructor_jolpica_id=dump.teams[team_id].reference,
            year=years[season_id],
            display_name=dump.teams[team_id].name,
            color_hex=normalise_color(dump.teams[team_id].primary_color),
        )
        for team_id, season_id in sorted(pairs, key=lambda p: (years[p[1]], p[0]))
    ]


# --------------------------------------------------------------------------- results


def position_text(entry: SessionEntryRow) -> str:
    """Ergast-style: the number when classified, else D (disqualified), W (withdrawn), N, R."""
    if entry.is_classified or (not entry.detail and not entry.status):
        return str(entry.position) if entry.position is not None else ""
    if entry.status == STATUS_DISQUALIFIED:
        return "D"
    if entry.status in STATUS_WITHDREW:
        return "W"
    if entry.status == STATUS_NOT_CLASSIFIED:
        return "N"
    return "R"


def _unique_positions(rows: list, *, rank_field: str | None = None) -> list:
    """Keep the first holder of each position (shared drives repeat one); later ones get None."""
    seen: set[int] = set()
    out = []
    ranked = False
    for row in rows:
        changes = {}
        if row.position is not None:
            if row.position in seen:
                changes["position"] = None
            else:
                seen.add(row.position)
        if rank_field and getattr(row, rank_field) == 1:
            if ranked:
                changes[rank_field] = None
            ranked = True
        out.append(replace(row, **changes) if changes else row)
    return out


class _Resolver:
    def __init__(self, dump: Dump):
        self.dump = dump

    def who(self, entry: SessionEntryRow) -> tuple[int, str, str]:
        """(driver id, driver reference, constructor reference) on race day."""
        try:
            round_entry = self.dump.round_entries[entry.round_entry_id]
            team_driver = self.dump.team_drivers[round_entry.team_driver_id]
            driver = self.dump.drivers[team_driver.driver_id]
            team = self.dump.teams[team_driver.team_id]
        except KeyError as exc:
            raise DumpError(f"Entry {entry.id} has a dangling reference {exc}") from exc
        return driver.id, driver.reference, team.reference


def map_results(dump: Dump, session: SessionRow) -> list[ResultData]:
    resolver = _Resolver(dump)
    rows = []
    for entry in sorted(
        dump.entries_by_session.get(session.id, []),
        key=lambda e: (e.position is None, e.position or 0, e.id),
    ):
        _, driver_ref, team_ref = resolver.who(entry)
        rank = entry.fastest_lap_rank if (entry.fastest_lap_rank or 0) >= 1 else None
        rows.append(
            ResultData(
                driver_jolpica_id=driver_ref,
                constructor_jolpica_id=team_ref,
                position=entry.position if (entry.position or 0) >= 1 else None,
                position_text=position_text(entry),
                grid=entry.grid,
                laps=entry.laps_completed,
                status=entry.detail,
                time_ms=parse_interval_ms(entry.time),
                best_lap_ms=parse_interval_ms(dump.fastest_laps.get(entry.id, "")),
                points=parse_points(entry.points),
                fastest_lap_rank=rank,
            )
        )
    # Positions can repeat in the 1950s (shared drives); the catalog needs them unique.
    return _unique_positions(_by_driver(rows), rank_field="fastest_lap_rank")


def _by_driver(rows: list) -> list:
    seen: set[str] = set()
    out = []
    for row in rows:
        if row.driver_jolpica_id not in seen:
            seen.add(row.driver_jolpica_id)
            out.append(row)
    return out


def merge_qualifying(dump: Dump, sessions: list[SessionRow]) -> list[QualifyingData]:
    """Merge Q1/Q2/Q3 (or the 1994-2005 sessions) into one row per driver.

    Sessions are ordered Q1, Q2, Q3 (or by number for QB/QO/QA); the n-th session supplies q<n>.
    The final position is the one from the last session the driver took part in.
    """
    resolver = _Resolver(dump)
    ordered = sorted(sessions, key=lambda s: (s.number or 0, s.type, s.id))
    merged: dict[int, dict] = {}
    for index, session in enumerate(ordered[:3]):
        for entry in dump.entries_by_session.get(session.id, []):
            driver_id, driver_ref, team_ref = resolver.who(entry)
            row = merged.setdefault(driver_id, {"driver": driver_ref, "q": [None, None, None]})
            row["constructor"] = team_ref
            if entry.position is not None and entry.position >= 1:
                row["position"] = entry.position
            row["q"][index] = parse_interval_ms(dump.fastest_laps.get(entry.id, ""))
    rows = [
        QualifyingData(
            driver_jolpica_id=v["driver"],
            constructor_jolpica_id=v["constructor"],
            position=v.get("position"),
            q1_ms=v["q"][0],
            q2_ms=v["q"][1],
            q3_ms=v["q"][2],
        )
        for v in merged.values()
    ]
    rows.sort(key=lambda r: (r.position is None, r.position or 0, r.driver_jolpica_id))
    return _unique_positions(rows)


# --------------------------------------------------------------------------- rounds


def map_round(dump: Dump, row: RoundRow, years: dict[int, int], *, today: dt.date) -> RoundBundle:
    circuit = dump.circuits[row.circuit_id].reference
    date = _date(row.date)
    sessions = [s for s in dump.sessions_by_round.get(row.id, []) if not s.is_cancelled]
    laps = next((s.scheduled_laps for s in sessions if s.type == "R"), None)
    data = RoundData(
        year=years[row.season_id],
        round=None if row.is_cancelled else row.number,
        name=row.name,
        circuit_jolpica_id=circuit,
        date=date,
        scheduled_laps=laps,
        is_cancelled=row.is_cancelled,
    )
    if row.is_cancelled:
        return RoundBundle(round=data)

    groups: dict[str, list[SessionRow]] = {}
    for s in sessions:
        kind = SESSION_TYPES.get(s.type)
        if kind is not None:
            groups.setdefault(kind, []).append(s)
    bundles = []
    for kind, members in sorted(groups.items()):
        has_entries = any(dump.entries_by_session.get(s.id) for s in members)
        if not has_entries and date < today and kind != "RACE":
            continue  # a past session the dump holds no data for
        starts = [t for t in (_start_utc(s.timestamp) for s in members) if t is not None]
        status = "results_final" if has_entries else ("finished" if date < today else "scheduled")
        session = SessionData(type=kind, start_utc=min(starts) if starts else None, status=status)
        if kind in ("Q", "SQ"):
            bundles.append(SessionBundle(session, qualifying=merge_qualifying(dump, members)))
        else:
            results = map_results(dump, members[0])
            bundles.append(SessionBundle(session, results=results))
    return RoundBundle(round=data, sessions=bundles)


def iter_rounds(
    dump: Dump, rounds: Iterable[RoundRow], years: dict[int, int], *, today: dt.date
) -> Iterator[tuple[RoundRow, RoundBundle]]:
    for row in rounds:
        yield row, map_round(dump, row, years, today=today)


# --------------------------------------------------------------------------- standings


@dataclass(frozen=True)
class StandingsLine:
    jolpica_id: str  # driver or constructor reference
    position: int | None
    position_text: str
    points: Decimal
    wins: int
    podiums: int


@dataclass
class RoundStandings:
    drivers: list[StandingsLine] = field(default_factory=list)
    constructors: list[StandingsLine] = field(default_factory=list)


def _cumulative_podiums(
    dump: Dump, years: dict[int, int]
) -> dict[tuple[int, int], tuple[dict[int, int], dict[int, int]]]:
    """Podiums up to and including each round: per driver id and per team id (per car).

    Counted from race results, as the spec asks ("podia wyliczamy z Result").
    """
    result: dict[tuple[int, int], tuple[dict[int, int], dict[int, int]]] = {}
    by_year: dict[int, list[RoundRow]] = {}
    for row in dump.rounds:
        if row.season_id in years and row.number is not None and not row.is_cancelled:
            by_year.setdefault(years[row.season_id], []).append(row)
    for year, rounds in by_year.items():
        drivers: Counter[int] = Counter()
        teams: Counter[int] = Counter()
        for row in sorted(rounds, key=lambda r: r.number or 0):
            for session in dump.sessions_by_round.get(row.id, []):
                if session.type != "R":
                    continue
                for entry in dump.entries_by_session.get(session.id, []):
                    # A disqualified car keeps a position in the dump but is not classified.
                    if not entry.is_classified or entry.position is None or entry.position > 3:
                        continue
                    team_driver = dump.team_drivers[
                        dump.round_entries[entry.round_entry_id].team_driver_id
                    ]
                    drivers[team_driver.driver_id] += 1
                    teams[team_driver.team_id] += 1
            result[(year, row.number or 0)] = (dict(drivers), dict(teams))
    return result


def map_standings(
    dump: Dump, from_year: int | None, to_year: int | None
) -> dict[tuple[int, int], RoundStandings]:
    """Championship tables keyed by (year, round number), straight from the dump.

    The dump already applies the historical rules (dropped scores, shared drives, exclusions),
    which is why standings are imported and never recomputed.
    """
    years = season_years(dump, from_year, to_year)
    wanted = set(years.values())
    podiums = _cumulative_podiums(dump, years)
    tables: dict[tuple[int, int], RoundStandings] = {}

    for rows, ref_of, side in (
        (dump.driver_standings, lambda i: dump.drivers[i].reference, "drivers"),
        (dump.team_standings, lambda i: dump.teams[i].reference, "constructors"),
    ):
        for row in rows:
            if row.year not in wanted:
                continue
            driver_counts, team_counts = podiums.get((row.year, row.round_number), ({}, {}))
            counts = driver_counts if side == "drivers" else team_counts
            line = StandingsLine(
                jolpica_id=ref_of(row.entity_id),
                position=row.position,
                position_text=str(row.position) if row.position is not None else "",
                points=row.points,
                wins=row.wins,
                podiums=counts.get(row.entity_id, 0),
            )
            getattr(tables.setdefault((row.year, row.round_number), RoundStandings()), side).append(
                line
            )
    return tables

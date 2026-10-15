"""Read queries of the analytics module (OpenF1 data, seasons 2023 onwards).

Every selector costs a fixed number of queries (at most 6) regardless of the row count: rows are
read once with values_list() and combined in Python. Durations are integer milliseconds.
Selectors take the SessionHeader from `load_header` and return plain dicts that the API
serialises as they are.

Missing data raises AnalyticsNotFound, which carries the message for the 404 body.
"""

from __future__ import annotations

import statistics
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Max

from apps.catalog.lookups import SessionDriver, SessionHeader, get_session_header, session_drivers

from .models import Lap, PitStop, PositionSample, RaceControlMessage, Stint, WeatherSample

ANALYTICS_FROM_YEAR = 2023
WEATHER_MAX_POINTS = 120

COMPOUND_LETTERS = {
    Stint.Compound.SOFT: "S",
    Stint.Compound.MEDIUM: "M",
    Stint.Compound.HARD: "H",
    Stint.Compound.INTERMEDIATE: "I",
    Stint.Compound.WET: "W",
}

PRE_2023_MESSAGE = "Detailed analytics are available from the 2023 season"


class AnalyticsNotFound(Exception):
    def __init__(self, message: str, year: int):
        super().__init__(message)
        self.message = message
        self.analytics_available = year >= ANALYTICS_FROM_YEAR


def load_header(year: int, round_number: int, session_type: str) -> SessionHeader:
    header = get_session_header(year, round_number, session_type)
    if header is None:
        if year < ANALYTICS_FROM_YEAR:
            raise AnalyticsNotFound(PRE_2023_MESSAGE, year)
        raise AnalyticsNotFound("Round or session not found.", year)
    return header


def _no_data(header: SessionHeader) -> AnalyticsNotFound:
    if header.year < ANALYTICS_FROM_YEAR:
        return AnalyticsNotFound(PRE_2023_MESSAGE, header.year)
    return AnalyticsNotFound("No analytics data for this session yet.", header.year)


def _session_block(header: SessionHeader) -> dict[str, Any]:
    return {
        "year": header.year,
        "round": header.round,
        "round_name": header.round_name,
        "type": header.type,
        "status": header.status,
    }


def _driver_block(driver: SessionDriver) -> dict[str, Any]:
    return {
        "driver_id": driver.driver_id,
        "code": driver.code,
        "full_name": driver.full_name,
        "constructor_id": driver.constructor_id,
        "constructor_name": driver.constructor_name,
        "color_hex": driver.color_hex,
    }


# --- Shared lap data -------------------------------------------------------------------------


def _load_laps(session_id: int) -> dict[int, list[tuple]]:
    """Laps per driver id, ordered by lap number: (lap, start, duration, pit_out, s1, s2, s3)."""
    by_driver: dict[int, list[tuple]] = defaultdict(list)
    rows = (
        Lap.objects.filter(session_id=session_id)
        .order_by("driver_id", "lap_number")
        .values_list(
            "driver_id",
            "lap_number",
            "date_start",
            "duration_ms",
            "is_pit_out_lap",
            "sector1_ms",
            "sector2_ms",
            "sector3_ms",
        )
    )
    for driver_id, *rest in rows:
        by_driver[driver_id].append(tuple(rest))
    return by_driver


def _lap_windows(laps: list[tuple]) -> list[tuple[int, datetime | None, datetime | None]]:
    """(lap number, start, end) for one driver's laps.

    end = start + duration; when the duration is missing (OpenF1 often has none for lap 1) the
    end is the start of the next lap; when that is missing too the lap was not completed
    (retirement) and end is None. A missing start is taken from the end of the previous lap.
    """
    windows = []
    previous_end: datetime | None = None
    for index, (number, start, duration, *_rest) in enumerate(laps):
        start = start or previous_end
        end = None
        if start is not None and duration is not None:
            end = start + timedelta(milliseconds=duration)
        elif index + 1 < len(laps) and laps[index + 1][1] is not None:
            end = laps[index + 1][1]
        windows.append((number, start, end))
        previous_end = end
    return windows


def _lap_resolver(laps_by_driver: dict[int, list[tuple]]) -> Callable[[datetime], int]:
    """Map a timestamp to a lap number using the earliest start of each lap over all drivers."""
    earliest: dict[int, datetime] = {}
    for laps in laps_by_driver.values():
        for number, start, *_rest in laps:
            if start is not None and (number not in earliest or start < earliest[number]):
                earliest[number] = start
    starts: list[datetime] = []
    numbers: list[int] = []
    for number in sorted(earliest):
        if not starts or earliest[number] > starts[-1]:
            starts.append(earliest[number])
            numbers.append(number)

    def lap_for(ts: datetime) -> int:
        index = bisect_right(starts, ts)
        return numbers[index - 1] if index else 1

    return lap_for


def _neutralisations(
    messages: Iterable[tuple[datetime, int | None, str]],
    lap_for: Callable[[datetime], int],
    last_lap: int,
) -> list[dict[str, Any]]:
    """Safety car (SC) and virtual safety car (VSC) periods as inclusive lap ranges.

    Input are the "SafetyCar" race control messages in time order. "... DEPLOYED" opens a
    period of its kind, "... IN THIS LAP" (SC) or "... ENDING" (VSC) closes it on the lap of the
    message. The lap is the message's lap_number, or else derived from its time. A period that
    is never closed lasts until the last lap.
    """
    opened: dict[str, int] = {}
    periods: list[dict[str, Any]] = []
    for ts, lap_number, message in messages:
        text = message.upper()
        kind = "VSC" if ("VIRTUAL" in text or "VSC" in text) else "SC"
        lap = lap_number or lap_for(ts)
        if "DEPLOYED" in text:
            if kind == "SC" and "VSC" in opened:
                # A virtual safety car turned into a safety car: no "ending" message comes.
                start = opened.pop("VSC")
                periods.append({"kind": "VSC", "start_lap": start, "end_lap": max(start, lap)})
            opened.setdefault(kind, lap)
        elif "IN THIS LAP" in text or "ENDING" in text:
            start = opened.pop(kind, None)
            if start is not None:
                periods.append({"kind": kind, "start_lap": start, "end_lap": max(start, lap)})
    for kind, start in opened.items():
        periods.append({"kind": kind, "start_lap": start, "end_lap": max(start, last_lap)})
    periods.sort(key=lambda p: (p["start_lap"], p["kind"]))
    return periods


def _safety_car_messages(session_id: int) -> list[tuple[datetime, int | None, str]]:
    return list(
        RaceControlMessage.objects.filter(session_id=session_id, category__iexact="SafetyCar")
        .order_by("ts", "id")
        .values_list("ts", "lap_number", "message")
    )


# --- positions -------------------------------------------------------------------------------


def positions(header: SessionHeader) -> dict[str, Any]:
    """Position of every driver at the end of every lap (6 queries).

    Algorithm: a driver's lap n ends at date_start + duration (else at the start of lap n + 1).
    The position at the end of the lap is the last PositionSample of that driver with
    ts <= lap end (bisect over the driver's time-sorted samples). It is null when the lap has
    no end (the driver retired during it, so every later lap is null as well) or when no
    sample precedes the end. Arrays are aligned to `laps` (1..N, N = highest lap number).
    Pit stops are lap numbers per driver (from the pit stop's lap_number, else the lap
    containing its time). SC/VSC periods are inclusive lap ranges, see _neutralisations.
    """
    drivers = session_drivers(header.session_id, header.type)
    laps_by_driver = _load_laps(header.session_id)
    laps_by_driver = {
        d.driver_id: laps_by_driver[d.driver_id] for d in drivers if d.driver_id in laps_by_driver
    }
    if not laps_by_driver:
        raise _no_data(header)

    windows = {driver_id: _lap_windows(laps) for driver_id, laps in laps_by_driver.items()}
    last_lap = max(number for w in windows.values() for number, _s, _e in w)
    max_end = max((end for w in windows.values() for _n, _s, end in w if end), default=None)

    sample_ts: dict[int, list[datetime]] = defaultdict(list)
    sample_pos: dict[int, list[int]] = defaultdict(list)
    if max_end is not None:
        samples = (
            PositionSample.objects.filter(session_id=header.session_id, ts__lte=max_end)
            .order_by("ts")
            .values_list("driver_id", "ts", "position")
            .iterator(chunk_size=5000)
        )
        for driver_id, ts, position in samples:
            sample_ts[driver_id].append(ts)
            sample_pos[driver_id].append(position)

    pit_rows = list(
        PitStop.objects.filter(session_id=header.session_id)
        .order_by("date")
        .values_list("driver_id", "lap_number", "date")
    )
    lap_for = _lap_resolver(laps_by_driver)

    out_drivers = []
    for driver in drivers:
        if driver.driver_id not in windows:
            continue
        ts_list, pos_list = (
            sample_ts.get(driver.driver_id, []),
            sample_pos.get(driver.driver_id, []),
        )
        per_lap: list[int | None] = [None] * last_lap
        for number, _start, end in windows[driver.driver_id]:
            if end is None:
                continue
            index = bisect_right(ts_list, end)
            if index:
                per_lap[number - 1] = pos_list[index - 1]
        pit_laps = sorted(
            {lap or lap_for(date) for d_id, lap, date in pit_rows if d_id == driver.driver_id}
        )
        out_drivers.append({**_driver_block(driver), "positions": per_lap, "pit_laps": pit_laps})

    return {
        "session": _session_block(header),
        "laps": list(range(1, last_lap + 1)),
        "drivers": out_drivers,
        "neutralisations": _neutralisations(
            _safety_car_messages(header.session_id), lap_for, last_lap
        ),
    }


# --- laps ------------------------------------------------------------------------------------


def _summary(times: list[int]) -> dict[str, Any]:
    return {
        "count": len(times),
        "best_ms": min(times) if times else None,
        "median_ms": round(statistics.median(times), 1) if times else None,
        "stdev_ms": round(statistics.stdev(times), 1) if len(times) > 1 else None,
    }


def laps(header: SessionHeader, driver_codes: list[str], hide_slow: bool) -> dict[str, Any]:
    """Lap times per driver with sector times and a summary (5 queries).

    Laps without a duration are never returned. With hide_slow the pit-out laps, in laps (a lap
    with a pit stop, or the lap before a pit-out lap) and laps inside an SC/VSC period are
    dropped, so the summary describes the laps that are returned. `driver_codes` limits the
    drivers (empty = all). Arrays are aligned to `lap_numbers`.
    """
    drivers = session_drivers(header.session_id, header.type)
    laps_by_driver = _load_laps(header.session_id)
    if not any(d.driver_id in laps_by_driver for d in drivers):
        raise _no_data(header)
    last_lap = max(rows[-1][0] for rows in laps_by_driver.values())
    periods = _neutralisations(
        _safety_car_messages(header.session_id), _lap_resolver(laps_by_driver), last_lap
    )
    slow_laps = {n for p in periods for n in range(p["start_lap"], p["end_lap"] + 1)}
    pit_laps: dict[int, set[int]] = defaultdict(set)
    if hide_slow:
        for driver_id, lap in PitStop.objects.filter(
            session_id=header.session_id, lap_number__isnull=False
        ).values_list("driver_id", "lap_number"):
            pit_laps[driver_id].add(lap)

    wanted = {c.upper() for c in driver_codes}
    out = []
    for driver in drivers:
        rows = laps_by_driver.get(driver.driver_id)
        if not rows or (wanted and driver.code.upper() not in wanted):
            continue
        numbers, durations, s1, s2, s3 = [], [], [], [], []
        for index, (number, _start, duration, pit_out, *sectors) in enumerate(rows):
            if duration is None:
                continue
            if hide_slow:
                next_is_out = index + 1 < len(rows) and rows[index + 1][3]
                if (
                    pit_out
                    or next_is_out
                    or number in pit_laps[driver.driver_id]
                    or number in slow_laps
                ):
                    continue
            numbers.append(number)
            durations.append(duration)
            s1.append(sectors[0])
            s2.append(sectors[1])
            s3.append(sectors[2])
        out.append(
            {
                **_driver_block(driver),
                "lap_numbers": numbers,
                "duration_ms": durations,
                "sector1_ms": s1,
                "sector2_ms": s2,
                "sector3_ms": s3,
                "summary": _summary(durations),
            }
        )
    return {
        "session": _session_block(header),
        "hide_slow": hide_slow,
        "drivers": out,
        "neutralisations": periods,
    }


# --- stints ----------------------------------------------------------------------------------


def compound_letter(compound: str) -> str:
    return COMPOUND_LETTERS.get(compound, "?")  # type: ignore[arg-type]


def _driver_stints(rows: list[tuple], last_lap: int | None) -> list[dict[str, Any]]:
    """Stints of one driver (ordered by number) with gaps in the lap range filled in.

    A missing start is the previous stint's end + 1 (1 for the first); a missing end is the next
    stint's start - 1 (the driver's last lap for the final stint).
    """
    stints: list[dict[str, Any]] = []
    for index, (number, compound, start, end, age) in enumerate(rows):
        if start is None:
            start = (stints[-1]["lap_end"] or 0) + 1 if stints else 1
        if end is None:
            following = rows[index + 1][2] if index + 1 < len(rows) else None
            end = following - 1 if following else last_lap
        stints.append(
            {
                "stint_number": number,
                "compound": compound,
                "compound_letter": compound_letter(compound),
                "lap_start": start,
                "lap_end": end,
                "laps": end - start + 1 if end is not None and end >= start else None,
                "tyre_age_at_start": age,
            }
        )
    return stints


def _load_stints(session_id: int) -> dict[int, list[tuple]]:
    by_driver: dict[int, list[tuple]] = defaultdict(list)
    rows = (
        Stint.objects.filter(session_id=session_id)
        .order_by("driver_id", "stint_number")
        .values_list(
            "driver_id", "stint_number", "compound", "lap_start", "lap_end", "tyre_age_at_start"
        )
    )
    for driver_id, *rest in rows:
        by_driver[driver_id].append(tuple(rest))
    return by_driver


def _last_laps(session_id: int) -> dict[int, int]:
    return dict(
        Lap.objects.filter(session_id=session_id)
        .values_list("driver_id")
        .annotate(last=Max("lap_number"))
        .order_by()
    )


def stints(header: SessionHeader) -> dict[str, Any]:
    """Tyre strategy per driver in final order (4 queries)."""
    drivers = session_drivers(header.session_id, header.type)
    rows = _load_stints(header.session_id)
    if not any(d.driver_id in rows for d in drivers):
        raise _no_data(header)
    last_laps = _last_laps(header.session_id)
    return {
        "session": _session_block(header),
        "drivers": [
            {
                **_driver_block(d),
                "position": d.position,
                "stints": _driver_stints(rows[d.driver_id], last_laps.get(d.driver_id)),
            }
            for d in drivers
            if d.driver_id in rows
        ],
    }


# --- pit stops -------------------------------------------------------------------------------


def pit_stops(header: SessionHeader) -> dict[str, Any]:
    """Pit stop table and team ranking of the fastest stops (4 queries).

    method is "stop_duration" when any stop of the session has stop_ms (stationary time,
    published from the 2024 US GP), otherwise "lane_duration"; the ranking uses only that
    value, one row (the fastest stop) per constructor. The compound change comes from the
    stints: the stint containing the stop lap (or the last one starting at or before it) and
    the first stint starting after it.
    """
    drivers = session_drivers(header.session_id, header.type)
    by_id = {d.driver_id: d for d in drivers}
    stops = list(
        PitStop.objects.filter(session_id=header.session_id)
        .order_by("date")
        .values_list("driver_id", "date", "lap_number", "stop_ms", "lane_ms")
    )
    stint_rows = _load_stints(header.session_id)
    if not stops and not stint_rows:
        raise _no_data(header)
    last_laps = _last_laps(header.session_id) if stint_rows else {}
    stints_by_driver = {
        driver_id: _driver_stints(rows, last_laps.get(driver_id))
        for driver_id, rows in stint_rows.items()
    }

    method = "stop_duration" if any(s[3] is not None for s in stops) else "lane_duration"
    order = {d.driver_id: index for index, d in enumerate(drivers)}
    table = []
    for driver_id, date, lap, stop_ms, lane_ms in stops:
        driver = by_id.get(driver_id)
        if driver is None:
            continue
        before = after = None
        if lap is not None:
            for stint in stints_by_driver.get(driver_id, []):
                if stint["lap_start"] <= lap:
                    before = stint["compound"]
                elif after is None:
                    after = stint["compound"]
        table.append(
            {
                "driver_id": driver_id,
                "driver_code": driver.code,
                "constructor_id": driver.constructor_id,
                "constructor_name": driver.constructor_name,
                "color_hex": driver.color_hex,
                "lap": lap,
                "date": date,
                "stop_ms": stop_ms,
                "lane_ms": lane_ms,
                "compound_from": before,
                "compound_to": after,
            }
        )
    table.sort(key=lambda r: (order[r["driver_id"]], r["date"]))

    key = "stop_ms" if method == "stop_duration" else "lane_ms"
    best: dict[int, dict[str, Any]] = {}
    for row in table:
        value = row[key]
        if value is not None and (
            row["constructor_id"] not in best or value < best[row["constructor_id"]][key]
        ):
            best[row["constructor_id"]] = row
    ranking = [
        {
            "rank": rank,
            "constructor_id": row["constructor_id"],
            "constructor_name": row["constructor_name"],
            "color_hex": row["color_hex"],
            "driver_code": row["driver_code"],
            "lap": row["lap"],
            "duration_ms": row[key],
        }
        for rank, row in enumerate(sorted(best.values(), key=lambda r: r[key]), start=1)
    ]
    for row in table:
        del row["date"]
    return {
        "session": _session_block(header),
        "method": method,
        "stops": table,
        "ranking": ranking,
    }


# --- weather ---------------------------------------------------------------------------------


def downsample_indices(count: int, limit: int) -> list[int]:
    """At most `limit` evenly spread indices of range(count), always including first and last."""
    if count <= limit:
        return list(range(count))
    return [round(i * (count - 1) / (limit - 1)) for i in range(limit)]


def weather(header: SessionHeader) -> dict[str, Any]:
    """Weather samples downsampled to at most WEATHER_MAX_POINTS (2 queries)."""
    rows = list(
        WeatherSample.objects.filter(session_id=header.session_id)
        .order_by("ts")
        .values(
            "ts",
            "air_temperature",
            "track_temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "rainfall",
        )
    )
    if not rows:
        raise _no_data(header)
    return {
        "session": _session_block(header),
        "total_samples": len(rows),
        "samples": [rows[i] for i in downsample_indices(len(rows), WEATHER_MAX_POINTS)],
    }


# --- race control ----------------------------------------------------------------------------


def race_control(header: SessionHeader, category: str | None) -> dict[str, Any]:
    """Race control messages in time order, optionally of one category (2 queries).

    A session has a few hundred messages, so all are read once and filtered in Python;
    `categories` always lists every category of the session (for the filter control).
    """
    rows = list(
        RaceControlMessage.objects.filter(session_id=header.session_id)
        .order_by("ts", "id")
        .values_list(
            "ts", "lap_number", "category", "flag", "scope", "sector", "driver__code", "message"
        )
    )
    if not rows:
        raise _no_data(header)
    wanted = category.lower() if category else None
    return {
        "session": _session_block(header),
        "categories": sorted({row[2] for row in rows if row[2]}),
        "messages": [
            {
                "ts": ts,
                "lap_number": lap,
                "category": cat,
                "flag": flag,
                "scope": scope,
                "sector": sector,
                "driver_code": code or None,
                "message": message,
            }
            for ts, lap, cat, flag, scope, sector, code, message in rows
            if wanted is None or cat.lower() == wanted
        ],
    }

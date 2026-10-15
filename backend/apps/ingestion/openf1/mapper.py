"""Pure functions: OpenF1 rows to the row dataclasses of `apps.analytics.services`.

No I/O and no database. Rows that cannot be stored (no driver in the map, a required value
missing or out of range) map to None and the caller counts them as skipped.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from apps.analytics import services as analytics

from . import schemas as s

DriverMap = Mapping[int, int]  # OpenF1 driver_number -> catalog driver id

_SMALLINT_MAX = 32767


def parse_ts(value: str | None) -> dt.datetime | None:
    """ISO 8601 timestamp to an aware UTC datetime (naive input is taken as UTC)."""
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.replace(tzinfo=dt.UTC) if parsed.tzinfo is None else parsed.astimezone(dt.UTC)


def to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError, OverflowError):
        return None


def to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool) or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def small(value: Any, *, minimum: int = 0) -> int | None:
    """An integer that fits a positive small integer column, else None."""
    number = to_int(value)
    return number if number is not None and minimum <= number <= _SMALLINT_MAX else None


def ms(value: Any) -> int | None:
    """Seconds (float) to non-negative integer milliseconds."""
    try:
        result = analytics.seconds_to_ms(value)
    except (ArithmeticError, ValueError, TypeError):
        return None
    return result if result is not None and 0 <= result <= 2_147_483_647 else None


def text(value: Any, limit: int) -> str:
    return str(value).strip()[:limit] if value is not None else ""


def map_lap(row: s.Lap, session_id: int, drivers: DriverMap) -> analytics.LapRow | None:
    driver_id = drivers.get(row.driver_number) if row.driver_number is not None else None
    lap_number = small(row.lap_number, minimum=1)
    if driver_id is None or lap_number is None:
        return None
    return analytics.LapRow(
        session_id=session_id,
        driver_id=driver_id,
        lap_number=lap_number,
        duration_ms=ms(row.lap_duration),
        sector1_ms=ms(row.duration_sector_1),
        sector2_ms=ms(row.duration_sector_2),
        sector3_ms=ms(row.duration_sector_3),
        is_pit_out_lap=bool(row.is_pit_out_lap),
        date_start=parse_ts(row.date_start),
    )


def map_stint(row: s.Stint, session_id: int, drivers: DriverMap) -> analytics.StintRow | None:
    driver_id = drivers.get(row.driver_number) if row.driver_number is not None else None
    stint_number = small(row.stint_number, minimum=1)
    if driver_id is None or stint_number is None:
        return None
    lap_start = small(row.lap_start)
    lap_end = small(row.lap_end)
    if lap_start is not None and lap_end is not None and lap_end < lap_start:
        lap_end = None  # would violate the table's ordering check; keep the rest of the row
    return analytics.StintRow(
        session_id=session_id,
        driver_id=driver_id,
        stint_number=stint_number,
        compound=analytics.normalise_compound(row.compound),
        lap_start=lap_start,
        lap_end=lap_end,
        tyre_age_at_start=small(row.tyre_age_at_start),
    )


def map_pit(row: s.Pit, session_id: int, drivers: DriverMap) -> analytics.PitStopRow | None:
    driver_id = drivers.get(row.driver_number) if row.driver_number is not None else None
    date = parse_ts(row.date)
    if driver_id is None or date is None:
        return None
    lane = row.lane_duration if row.lane_duration is not None else row.pit_duration
    return analytics.PitStopRow(
        session_id=session_id,
        driver_id=driver_id,
        date=date,
        lap_number=small(row.lap_number, minimum=1),
        stop_ms=ms(row.stop_duration),  # null before the 2024 US GP
        lane_ms=ms(lane),
    )


def map_position(
    row: s.Position, session_id: int, drivers: DriverMap
) -> analytics.PositionRow | None:
    driver_id = drivers.get(row.driver_number) if row.driver_number is not None else None
    ts = parse_ts(row.date)
    position = small(row.position, minimum=1)
    if driver_id is None or ts is None or position is None:
        return None
    return analytics.PositionRow(
        session_id=session_id, driver_id=driver_id, ts=ts, position=position
    )


def map_interval(
    row: s.Interval, session_id: int, drivers: DriverMap
) -> analytics.IntervalRow | None:
    driver_id = drivers.get(row.driver_number) if row.driver_number is not None else None
    ts = parse_ts(row.date)
    if driver_id is None or ts is None:
        return None
    gap_ms, gap_text = analytics.parse_gap(row.gap_to_leader)
    int_ms, int_text = analytics.parse_gap(row.interval)
    return analytics.IntervalRow(
        session_id=session_id,
        driver_id=driver_id,
        ts=ts,
        gap_to_leader_ms=gap_ms,
        gap_to_leader_text=gap_text,
        interval_ms=int_ms,
        interval_text=int_text,
    )


def map_race_control(
    row: s.RaceControl, session_id: int, drivers: DriverMap
) -> analytics.RaceControlRow | None:
    ts = parse_ts(row.date)
    message = (row.message or "").strip()
    if ts is None or not message:
        return None
    # A message about a driver we cannot identify is kept, without the driver link.
    driver_id = drivers.get(row.driver_number) if row.driver_number is not None else None
    return analytics.RaceControlRow(
        session_id=session_id,
        ts=ts,
        message=message,
        driver_id=driver_id,
        lap_number=small(row.lap_number, minimum=1),
        category=text(row.category, 40),
        flag=text(row.flag, 40),
        scope=text(row.scope, 40),
        sector=small(row.sector),
        qualifying_phase=small(row.qualifying_phase),
    )


def map_weather(row: s.Weather, session_id: int) -> analytics.WeatherRow | None:
    ts = parse_ts(row.date)
    if ts is None:
        return None
    return analytics.WeatherRow(
        session_id=session_id,
        ts=ts,
        air_temperature=to_float(row.air_temperature),
        track_temperature=to_float(row.track_temperature),
        humidity=to_float(row.humidity),
        pressure=to_float(row.pressure),
        wind_speed=to_float(row.wind_speed),
        wind_direction=small(row.wind_direction),
        rainfall=bool(to_int(row.rainfall)),
    )

"""Raw OpenF1 rows as frozen dataclasses.

Tolerant by design: unknown fields are dropped and missing ones become None, so an API change
only ever breaks `mapper.py`, never parsing. Values stay as received (seconds as floats,
timestamps as ISO strings); `mapper.py` converts them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from typing import Any, Self


@dataclass(frozen=True)
class _Row:
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(**{f.name: data.get(f.name) for f in fields(cls)})

    @classmethod
    def parse_all(cls, rows: Iterable[Mapping[str, Any]]) -> list[Self]:
        return [cls.from_dict(r) for r in rows if isinstance(r, Mapping)]


@dataclass(frozen=True)
class Meeting(_Row):
    meeting_key: int | None = None
    meeting_name: str | None = None
    meeting_official_name: str | None = None
    location: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    circuit_short_name: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    year: int | None = None
    is_cancelled: bool | None = None


@dataclass(frozen=True)
class Session(_Row):
    session_key: int | None = None
    session_type: str | None = None
    session_name: str | None = None
    meeting_key: int | None = None
    date_start: str | None = None
    date_end: str | None = None
    year: int | None = None
    is_cancelled: bool | None = None


@dataclass(frozen=True)
class Driver(_Row):
    session_key: int | None = None
    driver_number: int | None = None
    name_acronym: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    broadcast_name: str | None = None
    team_name: str | None = None


@dataclass(frozen=True)
class Lap(_Row):
    driver_number: int | None = None
    lap_number: int | None = None
    lap_duration: float | None = None
    duration_sector_1: float | None = None
    duration_sector_2: float | None = None
    duration_sector_3: float | None = None
    is_pit_out_lap: bool | None = None
    date_start: str | None = None


@dataclass(frozen=True)
class Stint(_Row):
    driver_number: int | None = None
    stint_number: int | None = None
    compound: str | None = None
    lap_start: int | None = None
    lap_end: int | None = None
    tyre_age_at_start: int | None = None


@dataclass(frozen=True)
class Pit(_Row):
    driver_number: int | None = None
    date: str | None = None
    lap_number: int | None = None
    lane_duration: float | None = None
    stop_duration: float | None = None
    pit_duration: float | None = None  # deprecated copy of lane_duration


@dataclass(frozen=True)
class Position(_Row):
    driver_number: int | None = None
    date: str | None = None
    position: int | None = None


@dataclass(frozen=True)
class Interval(_Row):
    driver_number: int | None = None
    date: str | None = None
    gap_to_leader: float | str | None = None
    interval: float | str | None = None


@dataclass(frozen=True)
class RaceControl(_Row):
    date: str | None = None
    driver_number: int | None = None
    lap_number: int | None = None
    category: str | None = None
    flag: str | None = None
    scope: str | None = None
    sector: int | None = None
    qualifying_phase: int | None = None
    message: str | None = None


@dataclass(frozen=True)
class Weather(_Row):
    date: str | None = None
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    rainfall: int | bool | None = None

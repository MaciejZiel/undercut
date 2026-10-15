"""Idempotent bulk writers for OpenF1 analytics data.

Every function can be run again for the same session and converges to the same rows, so the
import may be retried or re-delivered safely. Inputs are plain dataclasses; the ingestion
module maps OpenF1 JSON onto them (including driver_number -> driver id).
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from itertools import islice

from django.db import transaction
from django.db.models import Model

from .models import (
    IntervalSample,
    Lap,
    PitStop,
    PositionSample,
    RaceControlMessage,
    Stint,
    WeatherSample,
)

BATCH_SIZE = 2000


def seconds_to_ms(value: float | int | str | None) -> int | None:
    """OpenF1 durations are float seconds; we store integer milliseconds."""
    if value is None or value == "":
        return None
    ms = (Decimal(str(value)) * 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(ms)


def parse_gap(value: float | int | str | None) -> tuple[int | None, str]:
    """A gap is a number of seconds, a text like "+1 LAP", or missing."""
    if value is None or value == "":
        return None, ""
    if isinstance(value, str):
        try:
            return seconds_to_ms(value), ""
        except ArithmeticError:
            return None, value[:16]
    return seconds_to_ms(value), ""


def _batches(rows: Iterable[Model], size: int = BATCH_SIZE) -> Iterator[list[Model]]:
    iterator = iter(rows)
    while batch := list(islice(iterator, size)):
        yield batch


def _upsert(model, rows: Iterable[Model], unique_fields: list[str], update_fields: list[str]):
    total = 0
    with transaction.atomic():
        for batch in _batches(rows):
            model.objects.bulk_create(
                batch,
                update_conflicts=True,
                unique_fields=unique_fields,
                update_fields=update_fields,
            )
            total += len(batch)
    return total


@dataclass(frozen=True)
class LapRow:
    session_id: int
    driver_id: int
    lap_number: int
    duration_ms: int | None = None
    sector1_ms: int | None = None
    sector2_ms: int | None = None
    sector3_ms: int | None = None
    is_pit_out_lap: bool = False
    date_start: datetime | None = None


def upsert_laps(rows: Iterable[LapRow]) -> int:
    return _upsert(
        Lap,
        (Lap(**vars(r)) for r in rows),
        ["session", "driver", "lap_number"],
        ["duration_ms", "sector1_ms", "sector2_ms", "sector3_ms", "is_pit_out_lap", "date_start"],
    )


@dataclass(frozen=True)
class StintRow:
    session_id: int
    driver_id: int
    stint_number: int
    compound: str = Stint.Compound.UNKNOWN
    lap_start: int | None = None
    lap_end: int | None = None
    tyre_age_at_start: int | None = None


def normalise_compound(value: str | None) -> str:
    candidate = (value or "").strip().upper()
    return candidate if candidate in Stint.Compound.values else Stint.Compound.UNKNOWN


def upsert_stints(rows: Iterable[StintRow]) -> int:
    return _upsert(
        Stint,
        (Stint(**{**vars(r), "compound": normalise_compound(r.compound)}) for r in rows),
        ["session", "driver", "stint_number"],
        ["compound", "lap_start", "lap_end", "tyre_age_at_start"],
    )


@dataclass(frozen=True)
class PitStopRow:
    session_id: int
    driver_id: int
    date: datetime
    lap_number: int | None = None
    stop_ms: int | None = None
    lane_ms: int | None = None


def upsert_pit_stops(rows: Iterable[PitStopRow]) -> int:
    return _upsert(
        PitStop,
        (PitStop(**vars(r)) for r in rows),
        ["session", "driver", "date"],
        ["lap_number", "stop_ms", "lane_ms"],
    )


@dataclass(frozen=True)
class PositionRow:
    session_id: int
    driver_id: int
    ts: datetime
    position: int


def upsert_positions(rows: Iterable[PositionRow]) -> int:
    return _upsert(
        PositionSample,
        (PositionSample(**vars(r)) for r in rows),
        ["session", "driver", "ts"],
        ["position"],
    )


@dataclass(frozen=True)
class IntervalRow:
    session_id: int
    driver_id: int
    ts: datetime
    gap_to_leader_ms: int | None = None
    gap_to_leader_text: str = ""
    interval_ms: int | None = None
    interval_text: str = ""


def upsert_intervals(rows: Iterable[IntervalRow]) -> int:
    return _upsert(
        IntervalSample,
        (IntervalSample(**vars(r)) for r in rows),
        ["session", "driver", "ts"],
        ["gap_to_leader_ms", "gap_to_leader_text", "interval_ms", "interval_text"],
    )


@dataclass(frozen=True)
class WeatherRow:
    session_id: int
    ts: datetime
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    wind_speed: float | None = None
    wind_direction: int | None = None
    rainfall: bool = False


def upsert_weather(rows: Iterable[WeatherRow]) -> int:
    return _upsert(
        WeatherSample,
        (WeatherSample(**vars(r)) for r in rows),
        ["session", "ts"],
        [
            "air_temperature",
            "track_temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "rainfall",
        ],
    )


@dataclass(frozen=True)
class RaceControlRow:
    session_id: int
    ts: datetime
    message: str
    driver_id: int | None = None
    lap_number: int | None = None
    category: str = ""
    flag: str = ""
    scope: str = ""
    sector: int | None = None
    qualifying_phase: int | None = None


def insert_race_control(rows: Iterable[RaceControlRow]) -> int:
    """Messages are immutable and have no source id, so existing ones are left as they are."""
    created = 0
    with transaction.atomic():
        for batch in _batches(RaceControlMessage(**vars(r)) for r in rows):
            before = RaceControlMessage.objects.count()
            RaceControlMessage.objects.bulk_create(batch, ignore_conflicts=True)
            created += RaceControlMessage.objects.count() - before
    return created

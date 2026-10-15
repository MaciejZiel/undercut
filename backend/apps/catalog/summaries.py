"""Read-only race summaries for other modules (e-mails, demo data). No model imports needed.

Every function costs a fixed number of queries and returns plain frozen dataclasses.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.db.models import F, Max, Q

from .models import Result, Round, Session



def _classified(r: Result) -> bool:
    """Classified finish: a position and no retirement/disqualification marker."""
    return r.position is not None and (r.position_text == "" or r.position_text.isdigit())


@dataclass(frozen=True)
class RoundHeader:
    round_id: int
    year: int
    round: int | None
    name: str


@dataclass(frozen=True)
class PodiumEntry:
    position: int
    driver_id: int
    driver_name: str
    constructor_id: int
    constructor_name: str


@dataclass(frozen=True)
class FastestLap:
    driver_id: int
    driver_name: str
    constructor_name: str
    time_ms: int | None


@dataclass(frozen=True)
class RaceSummary:
    header: RoundHeader
    podium: list[PodiumEntry]
    fastest_lap: FastestLap | None

    @property
    def has_result(self) -> bool:
        return bool(self.podium)


@dataclass(frozen=True)
class DriverRaceResult:
    driver_id: int
    driver_name: str
    constructor_name: str
    position: int | None  # None when not classified
    position_text: str  # "R", "D", ... when not classified
    grid: int | None
    points: float
    status: str

    @property
    def grid_change(self) -> int | None:
        """Places gained (positive) or lost (negative); None when unknown or not classified."""
        if self.position is None or not self.grid:
            return None
        return self.grid - self.position


@dataclass(frozen=True)
class ConstructorRaceResult:
    constructor_id: int
    constructor_name: str
    best_position: int | None
    points: float
    cars: list[DriverRaceResult]


def round_header(round_id: int) -> RoundHeader | None:
    row = Round.objects.filter(pk=round_id).values("id", "season__year", "round", "name").first()
    if row is None:
        return None
    return RoundHeader(row["id"], row["season__year"], row["round"], row["name"])


def _race_rows(round_id: int):
    return Result.objects.filter(session__round_id=round_id, session__type=Session.Type.RACE)


def race_summary(round_id: int) -> RaceSummary | None:
    """Podium (team on race day) and fastest lap of a round's race; None for an unknown round."""
    header = round_header(round_id)
    if header is None:
        return None
    rows = list(
        _race_rows(round_id)
        .filter(Q(position__lte=3) | Q(fastest_lap_rank=1))
        .select_related("driver", "constructor")
        .order_by(F("position").asc(nulls_last=True))
    )
    podium = [
        PodiumEntry(
            position=r.position,
            driver_id=r.driver_id,
            driver_name=str(r.driver),
            constructor_id=r.constructor_id,
            constructor_name=r.constructor.name,
        )
        for r in rows
        if _classified(r) and r.position <= 3
    ]
    fastest = next((r for r in rows if r.fastest_lap_rank == 1), None)
    return RaceSummary(
        header=header,
        podium=podium,
        fastest_lap=None
        if fastest is None
        else FastestLap(
            fastest.driver_id, str(fastest.driver), fastest.constructor.name, fastest.best_lap_ms
        ),
    )


def _driver_result(r: Result) -> DriverRaceResult:
    return DriverRaceResult(
        driver_id=r.driver_id,
        driver_name=str(r.driver),
        constructor_name=r.constructor.name,
        position=r.position if _classified(r) else None,
        position_text=r.position_text,
        grid=r.grid,
        points=float(r.points),
        status=r.status,
    )


def driver_results(round_id: int, driver_ids) -> dict[int, DriverRaceResult]:
    """Race result per driver id (drivers that did not start are absent). One query."""
    rows = _race_rows(round_id).filter(driver_id__in=list(driver_ids))
    return {r.driver_id: _driver_result(r) for r in rows.select_related("driver", "constructor")}


def constructor_results(round_id: int, constructor_ids) -> dict[int, ConstructorRaceResult]:
    """Race result per constructor id: best finish, points of both cars and each car. One query."""
    rows = _race_rows(round_id).filter(constructor_id__in=list(constructor_ids))
    grouped: dict[int, list[Result]] = {}
    for r in rows.select_related("driver", "constructor").order_by(
        F("position").asc(nulls_last=True), "driver_id"
    ):
        grouped.setdefault(r.constructor_id, []).append(r)
    out = {}
    for constructor_id, results in grouped.items():
        cars = [_driver_result(r) for r in results]
        positions = [c.position for c in cars if c.position is not None]
        out[constructor_id] = ConstructorRaceResult(
            constructor_id=constructor_id,
            constructor_name=results[0].constructor.name,
            best_position=min(positions) if positions else None,
            points=sum(c.points for c in cars),
            cars=cars,
        )
    return out


def favourite_positions(round_ids, driver_id: int) -> dict[int, int | None]:
    """A driver's classified race position per round id (None when not classified). One query."""
    rows = _race_rows_for(round_ids).filter(driver_id=driver_id)
    return {
        r.session.round_id: r.position if _classified(r) else None
        for r in rows.select_related("session")
    }


def _race_rows_for(round_ids):
    return Result.objects.filter(
        session__round_id__in=list(round_ids), session__type=Session.Type.RACE
    )


def latest_completed_round_ids(limit: int = 3) -> list[int]:
    """Newest rounds whose race has results, newest first."""
    rows = (
        Result.objects.filter(session__type=Session.Type.RACE, position__isnull=False)
        .values("session__round_id")
        .annotate(date=Max("session__round__date"))
        .order_by("-date", "-session__round_id")[:limit]
    )
    return [row["session__round_id"] for row in rows]


def open_round_ids(now: dt.datetime, limit: int = 1) -> list[int]:
    """Rounds whose qualifying has not started yet (earliest first): predictions are open."""
    rows = (
        Session.objects.filter(
            type=Session.Type.Q,
            start_utc__gt=now,
            round__is_cancelled=False,
            round__round__isnull=False,
        )
        .order_by("start_utc")
        .values_list("round_id", flat=True)[:limit]
    )
    return list(rows)


def grid_driver_ids(round_id: int, limit: int = 10) -> list[int]:
    """Driver ids of a round's race in finishing order (classified first)."""
    rows = (
        _race_rows(round_id)
        .order_by(F("position").asc(nulls_last=True), "driver_id")
        .values_list("driver_id", flat=True)[:limit]
    )
    return list(rows)

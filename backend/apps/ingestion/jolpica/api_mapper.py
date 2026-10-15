"""Map Jolpica (Ergast-style) API JSON onto catalog service inputs.

Quirks handled here: every number is a string, optional keys are omitted instead of null,
qualifying times are `m:ss.mmm` strings, retirements use positionText "R", the schedule
names sprint qualifying differently across seasons, and race start is `date` + `time` (UTC).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from apps.catalog.services import (
    CircuitData,
    ConstructorData,
    ConstructorSeasonData,
    DriverData,
    QualifyingData,
    ResultData,
    RoundData,
    SessionData,
)

from .mapper import _by_driver, _unique_positions, parse_interval_ms, parse_points

# Schedule key -> catalog Session.Type, and the assumed length used for `end_utc`
# (the API has no end time; results are polled from end + 1 h, so a slightly long guess is safe).
SCHEDULE_SESSIONS: dict[str, tuple[str, dt.timedelta]] = {
    "FirstPractice": ("FP1", dt.timedelta(hours=1)),
    "SecondPractice": ("FP2", dt.timedelta(hours=1)),
    "ThirdPractice": ("FP3", dt.timedelta(hours=1)),
    "SprintQualifying": ("SQ", dt.timedelta(minutes=45)),
    "SprintShootout": ("SQ", dt.timedelta(minutes=45)),
    "Sprint": ("SPRINT", dt.timedelta(minutes=45)),
    "Qualifying": ("Q", dt.timedelta(hours=1)),
}
RACE_LENGTH = dt.timedelta(hours=2)


def _int(value) -> int | None:
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _utc(date: str | None, time: str | None) -> dt.datetime | None:
    """`2024-03-02` + `15:00:00Z` -> aware UTC datetime. No time means "unknown"."""
    if not date or not time:
        return None
    text = f"{date}T{time}".replace("Z", "+00:00")
    try:
        moment = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=dt.UTC)


# --------------------------------------------------------------------------- reference data


def circuit_data(circuit: dict) -> CircuitData:
    location = circuit.get("Location", {})

    def coordinate(key: str) -> Decimal | None:
        try:
            return Decimal(location[key])
        except (KeyError, InvalidOperation):
            return None

    return CircuitData(
        jolpica_id=circuit["circuitId"],
        name=circuit.get("circuitName", ""),
        locality=location.get("locality", ""),
        country=location.get("country", ""),
        lat=coordinate("lat"),
        lng=coordinate("long"),
    )


def driver_data(driver: dict) -> DriverData:
    dob = None
    try:
        dob = dt.date.fromisoformat(driver.get("dateOfBirth", ""))
    except ValueError:
        pass
    return DriverData(
        jolpica_id=driver["driverId"],
        given_name=driver.get("givenName", ""),
        family_name=driver.get("familyName", ""),
        code=driver.get("code", ""),
        permanent_number=_int(driver.get("permanentNumber")),
        dob=dob,
        nationality=driver.get("nationality", ""),
    )


def constructor_data(constructor: dict) -> ConstructorData:
    return ConstructorData(
        jolpica_id=constructor["constructorId"],
        name=constructor.get("name", ""),
        nationality=constructor.get("nationality", ""),
    )


# --------------------------------------------------------------------------- schedule


@dataclass(frozen=True)
class ScheduledRace:
    round: RoundData
    circuit: CircuitData
    sessions: list[SessionData]


def parse_schedule(mrdata: dict) -> list[ScheduledRace]:
    races = []
    for race in mrdata.get("RaceTable", {}).get("Races", []):
        number = _int(race.get("round"))
        if number is None:
            continue
        date = dt.date.fromisoformat(race["date"])
        circuit = circuit_data(race["Circuit"])
        sessions = []
        for key, (session_type, length) in SCHEDULE_SESSIONS.items():
            slot = race.get(key)
            if not slot:
                continue
            start = _utc(slot.get("date"), slot.get("time"))
            sessions.append(
                SessionData(
                    type=session_type,
                    start_utc=start,
                    end_utc=start + length if start else None,
                    status=None,
                )
            )
        race_start = _utc(race["date"], race.get("time"))
        sessions.append(
            SessionData(
                type="RACE",
                start_utc=race_start,
                end_utc=race_start + RACE_LENGTH if race_start else None,
                status=None,
            )
        )
        races.append(
            ScheduledRace(
                round=RoundData(
                    year=int(race["season"]),
                    round=number,
                    name=race.get("raceName", ""),
                    circuit_jolpica_id=circuit.jolpica_id,
                    date=date,
                ),
                circuit=circuit,
                sessions=sessions,
            )
        )
    return races


# --------------------------------------------------------------------------- results


@dataclass
class ParsedResults:
    """Rows plus the reference data they mention, so new drivers or teams can be created first."""

    rows: list = field(default_factory=list)
    drivers: dict[str, DriverData] = field(default_factory=dict)
    constructors: dict[str, ConstructorData] = field(default_factory=dict)


def _races(mrdata: dict) -> list[dict]:
    return mrdata.get("RaceTable", {}).get("Races", [])


def parse_race_results(mrdata: dict, key: str = "Results") -> ParsedResults:
    """Race (`Results`) or sprint (`SprintResults`) rows."""
    parsed = ParsedResults()
    rows: list[ResultData] = []
    for race in _races(mrdata):
        for item in race.get(key, []):
            driver, constructor = item["Driver"], item["Constructor"]
            parsed.drivers[driver["driverId"]] = driver_data(driver)
            parsed.constructors[constructor["constructorId"]] = constructor_data(constructor)
            fastest = item.get("FastestLap", {})
            rank = _int(fastest.get("rank"))
            time = item.get("Time", {})
            position = _int(item.get("position"))
            rows.append(
                ResultData(
                    driver_jolpica_id=driver["driverId"],
                    constructor_jolpica_id=constructor["constructorId"],
                    position=position if (position or 0) >= 1 else None,
                    position_text=item.get("positionText", ""),
                    grid=_int(item.get("grid")),
                    laps=_int(item.get("laps")),
                    status=item.get("status", ""),
                    time_ms=_int(time.get("millis")),
                    best_lap_ms=parse_interval_ms(fastest.get("Time", {}).get("time", "")),
                    points=parse_points(item.get("points", "0")),
                    fastest_lap_rank=rank if (rank or 0) >= 1 else None,
                )
            )
    parsed.rows = _unique_positions(_by_driver(rows), rank_field="fastest_lap_rank")
    return parsed


def parse_qualifying(mrdata: dict) -> ParsedResults:
    parsed = ParsedResults()
    rows: list[QualifyingData] = []
    for race in _races(mrdata):
        for item in race.get("QualifyingResults", []):
            driver, constructor = item["Driver"], item["Constructor"]
            parsed.drivers[driver["driverId"]] = driver_data(driver)
            parsed.constructors[constructor["constructorId"]] = constructor_data(constructor)
            position = _int(item.get("position"))
            rows.append(
                QualifyingData(
                    driver_jolpica_id=driver["driverId"],
                    constructor_jolpica_id=constructor["constructorId"],
                    position=position if (position or 0) >= 1 else None,
                    q1_ms=parse_interval_ms(item.get("Q1", "")),
                    q2_ms=parse_interval_ms(item.get("Q2", "")),
                    q3_ms=parse_interval_ms(item.get("Q3", "")),
                )
            )
    parsed.rows = _unique_positions(_by_driver(rows))
    return parsed


def race_constructors_by_year(parsed: ParsedResults, year: int) -> Iterable[ConstructorSeasonData]:
    for constructor in parsed.constructors.values():
        yield ConstructorSeasonData(constructor_jolpica_id=constructor.jolpica_id, year=year)


# --------------------------------------------------------------------------- standings


@dataclass(frozen=True)
class StandingLine:
    jolpica_id: str
    position: int | None
    position_text: str
    points: Decimal
    wins: int
    driver: DriverData | None = None
    constructor: ConstructorData | None = None


def parse_standings(mrdata: dict) -> tuple[list[StandingLine], list[StandingLine]]:
    """(driver lines, constructor lines) of the first standings list in the response."""
    lists = mrdata.get("StandingsTable", {}).get("StandingsLists", [])
    if not lists:
        return [], []
    table = lists[0]
    drivers, constructors = [], []
    for item in table.get("DriverStandings", []):
        driver = item["Driver"]
        position = _int(item.get("position"))
        drivers.append(
            StandingLine(
                jolpica_id=driver["driverId"],
                position=position,
                position_text=item.get("positionText", ""),
                points=parse_points(item.get("points", "0")),
                wins=_int(item.get("wins")) or 0,
                driver=driver_data(driver),
            )
        )
    for item in table.get("ConstructorStandings", []):
        constructor = item["Constructor"]
        constructors.append(
            StandingLine(
                jolpica_id=constructor["constructorId"],
                position=_int(item.get("position")),
                position_text=item.get("positionText", ""),
                points=parse_points(item.get("points", "0")),
                wins=_int(item.get("wins")) or 0,
                constructor=constructor_data(constructor),
            )
        )
    return drivers, constructors

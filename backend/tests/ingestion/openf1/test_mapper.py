import datetime as dt

import pytest

from apps.ingestion.openf1 import mapper
from apps.ingestion.openf1 import schemas as s

from .conftest import load

DRIVERS = {1: 100, 16: 116}


def test_schema_ignores_extra_and_missing_fields():
    lap = s.Lap.from_dict({"driver_number": 1, "lap_number": 2, "new_field": "x"})
    assert lap.lap_duration is None and lap.driver_number == 1
    assert s.Lap.parse_all([{"lap_number": 1}, "junk"]) == [s.Lap(lap_number=1)]


def test_lap_seconds_become_milliseconds():
    row = s.Lap.from_dict(load("laps")[0])
    out = mapper.map_lap(row, 7, DRIVERS)
    assert (out.session_id, out.driver_id, out.lap_number) == (7, 100, 1)
    assert (out.duration_ms, out.sector1_ms, out.sector2_ms, out.sector3_ms) == (
        97759,
        32877,
        41266,
        23616,
    )
    assert out.date_start == dt.datetime(2024, 3, 2, 15, 3, 42, 341000, tzinfo=dt.UTC)
    assert out.is_pit_out_lap is False


def test_lap_without_known_driver_or_number_is_dropped():
    assert mapper.map_lap(s.Lap(driver_number=99, lap_number=1), 1, DRIVERS) is None
    assert mapper.map_lap(s.Lap(driver_number=1, lap_number=0), 1, DRIVERS) is None
    assert mapper.map_lap(s.Lap(driver_number=1), 1, DRIVERS) is None


def test_lap_with_missing_or_bad_durations_keeps_the_row():
    out = mapper.map_lap(
        s.Lap(driver_number=1, lap_number=3, lap_duration=None, duration_sector_1="abc"),
        1,
        DRIVERS,
    )
    assert out.duration_ms is None and out.sector1_ms is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SOFT", "SOFT"),
        ("medium", "MEDIUM"),
        (" Hard ", "HARD"),
        ("TEST_UNKNOWN", "UNKNOWN"),
        (None, "UNKNOWN"),
        ("INTERMEDIATE", "INTERMEDIATE"),
    ],
)
def test_compound_is_normalised(raw, expected):
    out = mapper.map_stint(s.Stint(driver_number=1, stint_number=1, compound=raw), 1, DRIVERS)
    assert out.compound == expected


def test_stint_with_inverted_laps_drops_lap_end():
    out = mapper.map_stint(
        s.Stint(driver_number=1, stint_number=2, lap_start=10, lap_end=5), 1, DRIVERS
    )
    assert (out.lap_start, out.lap_end) == (10, None)


def test_pit_uses_deprecated_duration_only_as_fallback():
    base = {"driver_number": 16, "date": "2024-03-02T15:06:11.115000+00:00", "lap_number": 1}
    new = mapper.map_pit(s.Pit(**base, lane_duration=36.6, stop_duration=2.4), 1, DRIVERS)
    assert (new.lane_ms, new.stop_ms) == (36600, 2400)
    old = mapper.map_pit(s.Pit(**base, pit_duration=25.2), 1, DRIVERS)
    assert (old.lane_ms, old.stop_ms) == (25200, None)  # stop_duration is null before 2024 US GP
    assert mapper.map_pit(s.Pit(driver_number=16), 1, DRIVERS) is None


@pytest.mark.parametrize(
    ("gap", "expected"),
    [(0.853, (853, "")), (None, (None, "")), ("+1 LAP", (None, "+1 LAP")), ("12.5", (12500, ""))],
)
def test_interval_gaps(gap, expected):
    row = s.Interval(
        driver_number=1, date="2024-03-02T15:04:00+00:00", gap_to_leader=gap, interval=1.5
    )
    out = mapper.map_interval(row, 1, DRIVERS)
    assert (out.gap_to_leader_ms, out.gap_to_leader_text) == expected
    assert out.interval_ms == 1500


def test_position_validation():
    ok = s.Position(driver_number=1, date="2024-03-02T15:03:49.260000+00:00", position=2)
    assert mapper.map_position(ok, 1, DRIVERS).position == 2
    assert (
        mapper.map_position(s.Position(driver_number=1, date=ok.date, position=0), 1, DRIVERS)
        is None
    )
    assert (
        mapper.map_position(s.Position(driver_number=5, date=ok.date, position=1), 1, DRIVERS)
        is None
    )


def test_race_control_without_driver_and_with_unknown_driver():
    base = {"date": "2024-03-02T14:06:41+00:00", "message": " PINK PADDING "}
    out = mapper.map_race_control(s.RaceControl(**base, flag="GREEN", scope="Track"), 1, DRIVERS)
    assert (out.message, out.driver_id, out.flag, out.scope, out.category) == (
        "PINK PADDING",
        None,
        "GREEN",
        "Track",
        "",
    )
    unknown = mapper.map_race_control(s.RaceControl(**base, driver_number=99), 1, DRIVERS)
    assert unknown.driver_id is None
    assert (
        mapper.map_race_control(s.RaceControl(date=base["date"], message=" "), 1, DRIVERS) is None
    )


def test_weather():
    out = mapper.map_weather(s.Weather.from_dict(load("weather")[0]), 3)
    assert (out.air_temperature, out.pressure, out.wind_direction, out.rainfall) == (
        18.3,
        1017.0,
        48,
        False,
    )
    assert (
        mapper.map_weather(s.Weather(rainfall=1, date="2024-03-02T15:00:00Z"), 3).rainfall is True
    )


@pytest.mark.parametrize("value", [None, "", "garbage"])
def test_parse_ts_rejects_bad_input(value):
    assert mapper.parse_ts(value) is None


def test_parse_ts_naive_is_utc():
    assert mapper.parse_ts("2024-03-02T15:00:00") == dt.datetime(2024, 3, 2, 15, tzinfo=dt.UTC)

from datetime import UTC, datetime, timedelta

import pytest

from apps.analytics import services
from apps.analytics.models import (
    IntervalSample,
    Lap,
    PitStop,
    PositionSample,
    RaceControlMessage,
    Stint,
    WeatherSample,
)
from tests.catalog.factories import DriverFactory, SessionFactory

T0 = datetime(2024, 3, 2, 15, 0, tzinfo=UTC)


@pytest.fixture
def session(db):
    return SessionFactory()


@pytest.fixture
def driver(db):
    return DriverFactory()


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("", None), (92.608, 92608), ("92.608", 92608), (0.0005, 1), (90, 90000)],
)
def test_seconds_to_ms(value, expected):
    assert services.seconds_to_ms(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, (None, "")),
        (12.345, (12345, "")),
        ("+1 LAP", (None, "+1 LAP")),
        ("3.5", (3500, "")),
        ("+10 LAPS EXTRA LONG TEXT", (None, "+10 LAPS EXTRA L")),  # cut to the column size
    ],
)
def test_parse_gap(value, expected):
    assert services.parse_gap(value) == expected


def test_normalise_compound_maps_unknown_values():
    assert services.normalise_compound("soft") == "SOFT"
    assert services.normalise_compound(" Hard ") == "HARD"
    assert services.normalise_compound("HYPERSOFT") == "UNKNOWN"
    assert services.normalise_compound(None) == "UNKNOWN"


@pytest.mark.django_db
def test_upsert_laps_is_idempotent_and_updates(session, driver):
    rows = [
        services.LapRow(session.id, driver.id, 1, duration_ms=95000, sector1_ms=30000),
        services.LapRow(session.id, driver.id, 2, duration_ms=94000, is_pit_out_lap=True),
    ]
    assert services.upsert_laps(rows) == 2
    assert services.upsert_laps(rows) == 2
    assert Lap.objects.count() == 2

    services.upsert_laps([services.LapRow(session.id, driver.id, 1, duration_ms=93000)])
    lap = Lap.objects.get(lap_number=1)
    assert lap.duration_ms == 93000
    assert lap.sector1_ms is None  # source value replaced, not merged


@pytest.mark.django_db
def test_bulk_writes_are_batched(session, driver, monkeypatch):
    monkeypatch.setattr(services, "BATCH_SIZE", 2)
    rows = [
        services.PositionRow(session.id, driver.id, T0 + timedelta(seconds=i), 1 + i % 3)
        for i in range(7)
    ]
    assert services.upsert_positions(rows) == 7
    assert services.upsert_positions(rows) == 7
    assert PositionSample.objects.count() == 7


@pytest.mark.django_db
def test_upsert_stints_normalises_compound(session, driver):
    services.upsert_stints(
        [
            services.StintRow(session.id, driver.id, 1, "medium", 1, 20, 0),
            services.StintRow(session.id, driver.id, 2, "WEIRD", 21, 50, 3),
        ]
    )
    assert list(Stint.objects.values_list("compound", flat=True)) == ["MEDIUM", "UNKNOWN"]


@pytest.mark.django_db
def test_upsert_pit_stops_keeps_missing_stop_duration_null(session, driver):
    services.upsert_pit_stops(
        [services.PitStopRow(session.id, driver.id, T0, lap_number=14, lane_ms=22100)]
    )
    stop = PitStop.objects.get()
    assert stop.stop_ms is None
    assert stop.lane_ms == 22100


@pytest.mark.django_db
def test_upsert_intervals_stores_text_gaps(session, driver):
    services.upsert_intervals(
        [
            services.IntervalRow(session.id, driver.id, T0, 5000, "", 1200, ""),
            services.IntervalRow(session.id, driver.id, T0 + timedelta(seconds=5), None, "+1 LAP"),
        ]
    )
    assert IntervalSample.objects.filter(gap_to_leader_text="+1 LAP").count() == 1


@pytest.mark.django_db
def test_upsert_weather_is_idempotent(session):
    row = services.WeatherRow(session.id, T0, air_temperature=21.5, rainfall=True)
    services.upsert_weather([row])
    services.upsert_weather([services.WeatherRow(session.id, T0, air_temperature=22.0)])
    sample = WeatherSample.objects.get()
    assert sample.air_temperature == 22.0
    assert sample.rainfall is False


@pytest.mark.django_db
def test_race_control_ignores_duplicates_including_driverless_messages(session, driver):
    rows = [
        services.RaceControlRow(session.id, T0, "GREEN LIGHT - PIT EXIT OPEN"),
        services.RaceControlRow(session.id, T0, "CAR 1 TIME DELETED", driver_id=driver.id),
    ]
    assert services.insert_race_control(rows) == 2
    assert services.insert_race_control(rows) == 0  # driverless rows must not duplicate either
    assert RaceControlMessage.objects.count() == 2

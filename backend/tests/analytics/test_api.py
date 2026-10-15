import time

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.analytics.models import (
    PitStop,
    PositionSample,
    RaceControlMessage,
    Stint,
    WeatherSample,
)
from tests.catalog import factories as f

from .test_selectors import add_driver, add_laps, add_rcm, at, make_session

pytestmark = pytest.mark.django_db

ENDPOINTS = ["positions", "laps", "stints", "pit-stops", "weather", "race-control"]
QUERY_CAP = 6


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def url(endpoint, year=2024, number=1):
    return f"/api/v1/rounds/{year}/{number}/analytics/{endpoint}/"


def build_race(drivers=20, laps=60, samples_per_driver=2000, status="results_final"):
    """A synthetic race: 10 teams with colours, laps, stints, pit stops, positions, messages."""
    session = make_session(status=status)
    teams = [f.ConstructorFactory(name=f"Team {i}") for i in range(10)]
    for team in teams:
        f.ConstructorSeasonFactory(
            constructor=team, season=session.round.season, color_hex="#abcdef"
        )
    people = [
        add_driver(session, f"D{i:02d}", i + 1, constructor=teams[i % 10], color=False)
        for i in range(drivers)
    ]
    lap_ms = 90_000
    split = laps // 2
    race_s = laps * lap_ms / 1000
    positions, stints, stops = [], [], []
    for index, driver in enumerate(people):
        add_laps(session, driver, [lap_ms + index * 10 + n for n in range(laps)], pit_out=(1,))
        step = race_s / samples_per_driver
        positions.extend(
            PositionSample(
                session=session,
                driver=driver,
                ts=at(-300 + k * step),
                position=(index + k // 50) % drivers + 1,
            )
            for k in range(samples_per_driver)
        )
        stints.append(
            Stint(
                session=session,
                driver=driver,
                stint_number=1,
                compound="MEDIUM",
                lap_start=1,
                lap_end=split,
            )
        )
        stints.append(
            Stint(
                session=session,
                driver=driver,
                stint_number=2,
                compound="HARD",
                lap_start=split + 1,
                lap_end=laps,
            )
        )
        stops.append(
            PitStop(
                session=session,
                driver=driver,
                date=at(split * 90),
                lap_number=split,
                stop_ms=2000 + index * 10,
                lane_ms=21_000 + index,
            )
        )
    PositionSample.objects.bulk_create(positions, batch_size=5000)
    Stint.objects.bulk_create(stints)
    PitStop.objects.bulk_create(stops)
    add_rcm(session, at(900), "SAFETY CAR DEPLOYED", lap=10)
    add_rcm(session, at(1000), "SAFETY CAR IN THIS LAP", lap=12)
    RaceControlMessage.objects.create(
        session=session, ts=at(5), message="GREEN", category="Flag", flag="GREEN"
    )
    WeatherSample.objects.bulk_create(
        WeatherSample(session=session, ts=at(i * 30), air_temperature=20.0, track_temperature=30.0)
        for i in range(400)
    )
    return session


# --- Performance -----------------------------------------------------------------------------


def test_all_endpoints_are_fast_and_cheap_on_a_full_race(client):
    build_race()
    assert PositionSample.objects.count() == 40_000
    timings = {}
    for endpoint in ENDPOINTS:
        with CaptureQueriesContext(connection) as queries:
            started = time.perf_counter()
            response = client.get(url(endpoint))
            timings[endpoint] = time.perf_counter() - started
        assert response.status_code == 200, (endpoint, response.content[:200])
        assert len(queries) <= QUERY_CAP, (endpoint, len(queries))
        assert timings[endpoint] < 0.5, (endpoint, timings[endpoint])
    print({k: round(v * 1000) for k, v in timings.items()})


def test_positions_on_a_full_race_has_expected_shape(client):
    build_race()
    body = client.get(url("positions")).json()
    assert body["laps"] == list(range(1, 61))
    assert len(body["drivers"]) == 20
    first = body["drivers"][0]
    assert len(first["positions"]) == 60 and None not in first["positions"]
    assert first["pit_laps"] == [30] and first["color_hex"] == "#abcdef"
    assert body["neutralisations"] == [{"kind": "SC", "start_lap": 10, "end_lap": 12}]
    assert body["session"] == {
        "year": 2024,
        "round": 1,
        "round_name": "Round 1",
        "type": "RACE",
        "status": "results_final",
    }


# --- Endpoints -------------------------------------------------------------------------------


def test_laps_query_parameters(client):
    build_race(drivers=4, laps=20, samples_per_driver=20)
    body = client.get(url("laps"), {"drivers": "d01,D02"}).json()
    assert [d["code"] for d in body["drivers"]] == ["D01", "D02"]
    assert body["hide_slow"] is True
    # Lap 1 is a pit-out lap, laps 10-12 are under SC.
    assert body["drivers"][0]["lap_numbers"] == [2, 3, 4, 5, 6, 7, 8, 9, *range(13, 21)]
    assert body["drivers"][0]["summary"]["best_ms"] == 90_010 + 1
    shown = client.get(url("laps"), {"drivers": "D01", "hide_slow": "false"}).json()
    assert shown["drivers"][0]["lap_numbers"] == list(range(1, 21))
    assert shown["hide_slow"] is False


def test_laps_rejects_bad_parameters(client):
    build_race(drivers=2, laps=3, samples_per_driver=3)
    assert client.get(url("laps"), {"drivers": "TOOLONG"}).status_code == 400
    assert client.get(url("laps"), {"hide_slow": "maybe"}).status_code == 400
    assert client.get(url("positions"), {"session": "FP1"}).status_code == 400


def test_stints_endpoint(client):
    build_race(drivers=3, laps=40, samples_per_driver=3)
    drivers = client.get(url("stints")).json()["drivers"]
    assert [d["code"] for d in drivers] == ["D00", "D01", "D02"]
    assert [(s["compound_letter"], s["laps"], s["lap_start"]) for s in drivers[0]["stints"]] == [
        ("M", 20, 1),
        ("H", 20, 21),
    ]


def test_pit_stops_endpoint_reports_the_method(client):
    session = build_race(drivers=4, laps=40, samples_per_driver=3)
    body = client.get(url("pit-stops")).json()
    assert body["method"] == "stop_duration"
    assert body["ranking"][0]["rank"] == 1 and body["ranking"][0]["duration_ms"] == 2000
    assert body["stops"][0]["compound_from"] == "MEDIUM"
    assert body["stops"][0]["compound_to"] == "HARD"
    PitStop.objects.filter(session=session).update(stop_ms=None)
    assert client.get(url("pit-stops")).json()["method"] == "lane_duration"


def test_weather_endpoint_downsamples(client):
    build_race(drivers=2, laps=3, samples_per_driver=3)
    body = client.get(url("weather")).json()
    assert body["total_samples"] == 400 and len(body["samples"]) == 120


def test_race_control_endpoint_filters_by_category(client):
    build_race(drivers=2, laps=3, samples_per_driver=3)
    body = client.get(url("race-control"), {"category": "safetycar"}).json()
    assert [m["message"] for m in body["messages"]] == [
        "SAFETY CAR DEPLOYED",
        "SAFETY CAR IN THIS LAP",
    ]
    assert body["categories"] == ["Flag", "SafetyCar"]
    assert body["messages"][0]["lap_number"] == 10 and body["messages"][0]["driver_code"] is None
    assert len(client.get(url("race-control")).json()["messages"]) == 3


def test_session_parameter_selects_the_session(client):
    build_race(drivers=2, laps=3, samples_per_driver=3)
    assert client.get(url("stints"), {"session": "SPRINT"}).status_code == 404
    assert client.get(url("stints"), {"session": "RACE"}).status_code == 200


# --- Cache headers ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "cached"),
    [("results_final", True), ("finished", True), ("live", False), ("scheduled", False)],
)
def test_cache_control_only_for_finished_sessions(client, status, cached):
    build_race(drivers=2, laps=3, samples_per_driver=3, status=status)
    response = client.get(url("positions"))
    assert response.status_code == 200
    if cached:
        assert response["Cache-Control"] == "public, max-age=60"
    else:
        assert "max-age=60" not in response.get("Cache-Control", "")


def test_errors_are_not_cached(client):
    assert "max-age" not in client.get(url("laps", year=2024, number=9)).get("Cache-Control", "")


# --- 404 -------------------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_pre_2023_season_message(client, endpoint):
    make_session(year=2019)
    for number in (1, 8):  # an existing round without data and a round that does not exist
        response = client.get(url(endpoint, year=2019, number=number))
        assert response.status_code == 404
        assert response.json() == {
            "detail": "Detailed analytics are available from the 2023 season",
            "analytics_available": False,
        }


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_missing_round_and_missing_data_in_a_supported_season(client, endpoint):
    make_session(year=2024, number=1)
    missing_round = client.get(url(endpoint, number=5))
    assert missing_round.status_code == 404
    assert missing_round.json() == {
        "detail": "Round or session not found.",
        "analytics_available": True,
    }
    no_data = client.get(url(endpoint))
    assert no_data.status_code == 404
    assert no_data.json() == {
        "detail": "No analytics data for this session yet.",
        "analytics_available": True,
    }


def test_race_control_with_unknown_category_is_empty_not_missing(client):
    session = make_session()
    add_rcm(session, at(1), "GREEN", category="Flag")
    response = client.get(url("race-control"), {"category": "Drs"})
    assert response.status_code == 200 and response.json()["messages"] == []


# --- Access and schema -----------------------------------------------------------------------


def test_endpoints_are_public_and_read_only(client):
    build_race(drivers=2, laps=3, samples_per_driver=3)
    assert client.post(url("positions")).status_code == 405
    assert client.get(url("positions")).status_code == 200

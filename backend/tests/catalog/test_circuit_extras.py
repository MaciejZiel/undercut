"""Derived lap record, estimated length and outline on the circuit page."""

import datetime as dt

import pytest
from rest_framework.test import APIClient

from apps.catalog import selectors

from . import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def race_on(circuit, year, *, best_lap_ms, rank=1, driver=None, date=None):
    season = f.SeasonFactory._meta.model.objects.filter(year=year).first() or f.SeasonFactory(
        year=year
    )
    rnd = f.RoundFactory(season=season, circuit=circuit, date=date or dt.date(year, 6, 1))
    session = f.SessionFactory(round=rnd)
    return f.ResultFactory(
        session=session,
        driver=driver or f.DriverFactory(given_name="Max", family_name=f"V{year}"),
        best_lap_ms=best_lap_ms,
        fastest_lap_rank=rank,
        position=1,
    )


def test_lap_record_is_the_fastest_race_lap_ever_set_there():
    circuit = f.CircuitFactory(slug="monza")
    race_on(circuit, 2019, best_lap_ms=83_000)
    race_on(circuit, 2020, best_lap_ms=81_500)
    race_on(circuit, 2021, best_lap_ms=84_000)
    record = selectors.circuit_lap_record(circuit)
    assert record["time_ms"] == 81_500
    assert record["year"] == 2020
    assert record["driver"] == "Max V2020"


def test_only_fastest_lap_results_count_and_no_data_means_no_record():
    circuit = f.CircuitFactory(slug="spa")
    assert selectors.circuit_lap_record(circuit) is None
    race_on(circuit, 2022, best_lap_ms=70_000, rank=2)  # not the race's fastest lap
    assert selectors.circuit_lap_record(circuit) is None


def test_a_hand_entered_record_wins():
    circuit = f.CircuitFactory(
        slug="imola", lap_record_ms=75_000, lap_record_driver="Someone", lap_record_year=2004
    )
    race_on(circuit, 2023, best_lap_ms=70_000)
    assert selectors.circuit_lap_record(circuit) == {
        "time_ms": 75_000,
        "driver": "Someone",
        "year": 2004,
    }


def test_length_prefers_the_real_value_and_rounds_the_estimate():
    assert selectors.circuit_length(f.CircuitFactory(length_m=5793)) == (5793, False)
    estimated = f.CircuitFactory(
        outline={"width": 1, "height": 1, "points": [[0, 0]], "length_m": 5062.7}
    )
    assert selectors.circuit_length(estimated) == (5100, True)
    assert selectors.circuit_length(f.CircuitFactory()) == (None, False)


def test_outline_is_exposed_only_when_it_has_points():
    assert selectors.circuit_outline(f.CircuitFactory()) is None
    assert selectors.circuit_outline(f.CircuitFactory(outline={"points": []})) is None
    shape = {"width": 1000, "height": 400, "points": [[0, 0], [1000, 400]], "length_m": 5000}
    assert selectors.circuit_outline(f.CircuitFactory(outline=shape)) == {
        "width": 1000,
        "height": 400,
        "points": [[0, 0], [1000, 400]],
        "marker": True,
        "origin": "openf1",
    }
    unmarked = {**shape, "marker": False, "origin": "geojson"}
    drawn = selectors.circuit_outline(f.CircuitFactory(outline=unmarked))
    assert drawn["marker"] is False and drawn["origin"] == "geojson"


def test_circuit_page_serialises_record_length_and_outline(client):
    circuit = f.CircuitFactory(
        slug="suzuka",
        outline={"width": 1000, "height": 600, "points": [[1, 2], [3, 4]], "length_m": 5807.4},
    )
    race_on(circuit, 2023, best_lap_ms=90_000)
    body = client.get("/api/v1/circuits/suzuka/").json()
    assert body["lap_record_ms"] == 90_000 and body["lap_record_year"] == 2023
    assert body["length_m"] == 5800 and body["length_is_estimate"] is True
    assert body["outline"] == {
        "width": 1000,
        "height": 600,
        "points": [[1, 2], [3, 4]],
        "marker": True,
        "origin": "openf1",
    }


def test_round_page_uses_the_estimated_length(client):
    circuit = f.CircuitFactory(
        outline={"width": 1, "height": 1, "points": [[0, 0]], "length_m": 4000}
    )
    rnd = f.RoundFactory(circuit=circuit, round=1, season=f.SeasonFactory(year=2025))
    body = client.get(f"/api/v1/rounds/2025/{rnd.round}/").json()
    assert body["circuit"]["length_m"] == 4000

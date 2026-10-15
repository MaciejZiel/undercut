import datetime as dt
import math

import pytest

from apps.catalog.models import Circuit
from apps.ingestion.openf1 import outline


def ring(n=370, radius=5000.0, stretch=2.0):
    """A closed lap shaped like an ellipse, sampled like OpenF1 (decimetres)."""
    return [
        (radius * stretch * math.cos(2 * math.pi * i / n), radius * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


def test_simplify_keeps_corners_and_drops_straight_points():
    line = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (3.0, 1.0), (3.0, 2.0), (3.0, 3.0)]
    assert outline.simplify(line, 0.1) == [(0.0, 0.0), (3.0, 0.0), (3.0, 3.0)]
    assert outline.simplify([(0.0, 0.0), (1.0, 1.0)], 0.1) == [(0.0, 0.0), (1.0, 1.0)]


def test_build_outline_fits_the_viewbox_and_closes_the_loop():
    result = outline.build_outline(ring())
    assert result["width"] == 1000 and 0 < result["height"] < 1000
    assert result["points"][0] == result["points"][-1]
    assert 20 < len(result["points"]) < 200
    assert all(0 <= x <= 1000 and 0 <= y <= 1000 for x, y in result["points"])


def test_length_is_measured_in_metres_from_decimetres():
    circle = [
        (5000 * math.cos(2 * math.pi * i / 400), 5000 * math.sin(2 * math.pi * i / 400))
        for i in range(400)
    ]
    expected = 2 * math.pi * 5000 / 10  # decimetres -> metres
    assert outline.build_outline(circle)["length_m"] == pytest.approx(expected, rel=0.01)


def test_y_axis_is_flipped_for_svg():
    samples = [(float(i), float(i)) for i in range(200)]
    samples += [(199.0 - i, 199.0 - i) for i in range(200)]
    points = outline.build_outline(samples)["points"]
    assert points[0] == [0, 1000]  # lowest map y is at the bottom of the picture


def test_unusable_laps_are_rejected():
    assert outline.build_outline(ring(n=50)) is None  # too few samples
    open_lap = [(float(i), 0.0) for i in range(300)]
    assert outline.build_outline(open_lap) is None  # does not come back to the start
    assert outline.build_outline([(1.0, 1.0)] * 300) is None  # standing still


def test_pick_lap_ignores_out_laps_and_takes_the_typical_one():
    laps = [
        {"lap_number": 1, "date_start": "t", "lap_duration": 120.0, "is_pit_out_lap": False},
        {"lap_number": 2, "date_start": "t", "lap_duration": 99.0, "is_pit_out_lap": False},
        {"lap_number": 3, "date_start": "t", "lap_duration": 98.0, "is_pit_out_lap": False},
        {"lap_number": 4, "date_start": "t", "lap_duration": 150.0, "is_pit_out_lap": True},
        {"lap_number": 5, "date_start": "t", "lap_duration": 140.0, "is_pit_out_lap": False},
        {"lap_number": 6, "date_start": None, "lap_duration": 98.5, "is_pit_out_lap": False},
    ]
    assert outline.pick_lap(laps)["lap_number"] in (2, 3)
    assert outline.pick_lap([]) is None
    assert outline.pick_lap([{"lap_number": 1, "date_start": "t", "lap_duration": 90}]) is None


class FakeClient:
    def __init__(self, samples):
        self.samples = samples
        self.calls = []

    def get(self, endpoint, params=None):
        self.calls.append((endpoint, dict(params or {})))
        if endpoint == "session_result":
            return [{"position": 1, "driver_number": 63}]
        if endpoint == "laps":
            return [
                {
                    "lap_number": n,
                    "date_start": "2026-10-11T12:10:36.014000+00:00",
                    "lap_duration": 99.0,
                    "is_pit_out_lap": False,
                }
                for n in (2, 3, 4)
            ]
        if endpoint == "location":
            return [
                {"date": f"2026-10-11T12:10:{i % 60:02d}.{i:03d}000+00:00", "x": x, "y": y}
                for i, (x, y) in enumerate(self.samples)
            ]
        return []


def test_fetch_outline_asks_for_the_winners_median_lap_only():
    client = FakeClient(ring())
    result = outline.fetch_outline(client, 11388)
    assert result and result["width"] == 1000
    endpoints = [c[0] for c in client.calls]
    assert endpoints == ["session_result", "laps", "location"]
    location = client.calls[2][1]
    assert location["driver_number"] == 63 and location["session_key"] == 11388
    start = dt.datetime.fromisoformat(location["date>="])
    stop = dt.datetime.fromisoformat(location["date<="])
    assert (stop - start).total_seconds() == pytest.approx(99.0)


def test_fetch_outline_gives_up_without_a_winner_or_laps():
    class Empty(FakeClient):
        def get(self, endpoint, params=None):
            return []

    assert outline.fetch_outline(Empty([]), 1) is None


@pytest.mark.django_db
def test_set_circuit_outline_stores_the_shape():
    from apps.catalog import services

    circuit = Circuit.objects.create(slug="marina-bay", name="Marina Bay")
    shape = {"width": 1000, "height": 500, "points": [[0, 0], [1000, 500]], "length_m": 4900}
    services.set_circuit_outline(circuit.id, shape)
    circuit.refresh_from_db()
    assert circuit.outline == shape

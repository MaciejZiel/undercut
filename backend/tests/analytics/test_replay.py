import json
import time

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.analytics import replay
from apps.analytics.models import IntervalSample, Lap, PitStop, PositionSample, Stint

from .test_selectors import add_driver, add_laps, add_rcm, at, make_session

pytestmark = pytest.mark.django_db

QUERY_CAP = 8


@pytest.fixture(autouse=True)
def _reset_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def replay_url(year=2024, number=1):
    return f"/api/v1/rounds/{year}/{number}/replay/"


def stint(session, driver, number, compound, lap_start, lap_end, age=0):
    return Stint(
        session=session,
        driver=driver,
        stint_number=number,
        compound=compound,
        lap_start=lap_start,
        lap_end=lap_end,
        tyre_age_at_start=age,
    )


@pytest.fixture
def race():
    """3 drivers, 5 laps; NOR pits in lap 2; LEC retires in lap 4; one SC period and a red flag.

    Lap starts (s): VER 0,100,200,300,400 (ends 500); NOR 0,101,202,303,404 (ends 505);
    LEC 0,100,200,300 (lap 4 never completed). Duration 505 s, step 5 -> 102 frames.
    """
    session = make_session(status="finished")
    ver = add_driver(session, "VER", 1)
    nor = add_driver(session, "NOR", 2)
    lec = add_driver(session, "LEC", 3)
    add_laps(session, ver, [100_000] * 5)
    add_laps(session, nor, [101_000] * 5)
    add_laps(session, lec, [100_000, 100_000, 100_000, None])
    Stint.objects.bulk_create(
        [
            stint(session, ver, 1, "MEDIUM", 1, 5, age=2),
            stint(session, nor, 1, "SOFT", 1, 2),
            stint(session, nor, 2, "HARD", 3, 5),
            stint(session, lec, 1, "SOFT", 1, 4),
        ]
    )
    PitStop.objects.create(session=session, driver=nor, date=at(190), lap_number=2, lane_ms=22_000)
    PositionSample.objects.bulk_create(
        [
            PositionSample(session=session, driver=ver, ts=at(-60), position=1),
            PositionSample(session=session, driver=nor, ts=at(-60), position=2),
            PositionSample(session=session, driver=nor, ts=at(250), position=3),
            PositionSample(session=session, driver=lec, ts=at(-60), position=3),
            PositionSample(session=session, driver=lec, ts=at(250), position=2),
        ]
    )
    IntervalSample.objects.bulk_create(
        [
            IntervalSample(session=session, driver=ver, ts=at(7), gap_to_leader_ms=0),
            IntervalSample(
                session=session,
                driver=nor,
                ts=at(7),
                gap_to_leader_ms=3500,
                interval_ms=3500,
            ),
            IntervalSample(session=session, driver=nor, ts=at(130), gap_to_leader_text="+1 LAP"),
        ]
    )
    add_rcm(session, at(150), "SAFETY CAR DEPLOYED", lap=2)
    add_rcm(session, at(260), "SAFETY CAR IN THIS LAP", lap=3)
    add_rcm(session, at(320), "RED FLAG", category="Flag", flag="RED", scope="Track", lap=4)
    return session


def fetch(client, **params):
    response = client.get(replay_url(), params)
    assert response.status_code == 200, response.content
    return response, response.json()


def expand(runs, count):
    out, k = [], 0
    for i in range(count):
        while k + 1 < len(runs["at"]) and runs["at"][k + 1] <= i:
            k += 1
        out.append(runs["v"][k])
    return out


def test_compact_encoding_shape(client, race):
    _, body = fetch(client)
    assert set(body) == {"session", "drivers", "frames", "events"}
    assert body["session"]["laps"] == 5
    assert body["session"]["duration_s"] == 505.0
    assert body["session"]["start"].startswith("2024-03-02T15:00:00")
    assert [d["code"] for d in body["drivers"]] == ["VER", "NOR", "LEC"]
    assert set(body["drivers"][0]) >= {"driver_id", "code", "full_name", "constructor_name"}
    assert body["drivers"][0]["color_hex"] == "#112233"
    frames = body["frames"]
    assert frames["step_s"] == 5 and frames["count"] == 102
    assert frames["t"][:3] == [0, 5, 10] and frames["t"][-1] == 505
    assert len(frames["drivers"]) == 3
    for block in frames["drivers"]:
        for dense in ("pos", "gap", "int"):
            assert len(block[dense]) == 102
        for runs in ("lap", "tyre", "age", "pit"):
            assert block[runs]["at"][0] == 0
            assert len(block[runs]["at"]) == len(block[runs]["v"])


def test_carry_forward_of_positions_and_gaps(client, race):
    _, body = fetch(client)
    ver, nor, lec = body["frames"]["drivers"]
    # pre-race samples (t = -60) feed frame 0
    assert (ver["pos"][0], nor["pos"][0], lec["pos"][0]) == (1, 2, 3)
    # NOR changes to P3 at t = 250 (frame 50), exactly on the frame: "at or before"
    assert nor["pos"][49] == 2 and nor["pos"][50] == 3 and nor["pos"][101] == 3
    assert lec["pos"][49] == 3 and lec["pos"][50] == 2
    # no interval sample before t = 7: null, then carried
    assert nor["gap"][1] is None and nor["gap"][2] == 3500 and nor["gap"][25] == 3500
    assert nor["int"][2] == 3500 and nor["int"][25] == 3500
    # a newer sample replaces both values (text gap, no interval)
    assert nor["gap"][26] == "+1 LAP" and nor["gap"][101] == "+1 LAP"
    assert nor["int"][26] is None
    assert ver["gap"][2] == 0 and ver["gap"][100] == 0
    assert lec["gap"] == [None] * 102


def test_lap_numbers_derived_from_lap_start_times(client, race):
    _, body = fetch(client)
    ver, nor, lec = body["frames"]["drivers"]
    assert ver["lap"] == {"at": [0, 20, 40, 60, 80], "v": [1, 2, 3, 4, 5]}
    assert nor["lap"] == {"at": [0, 21, 41, 61, 81], "v": [1, 2, 3, 4, 5]}
    # LEC stays on lap 4 after the retirement
    assert lec["lap"] == {"at": [0, 20, 40, 60], "v": [1, 2, 3, 4]}
    assert body["drivers"][2]["retired_t"] == 300.0
    assert body["drivers"][0]["retired_t"] is None


def test_tyre_compound_and_age(client, race):
    _, body = fetch(client)
    ver, nor, lec = body["frames"]["drivers"]
    assert ver["tyre"] == {"at": [0], "v": ["MEDIUM"]}
    assert expand(ver["age"], 102)[::20][:5] == [2, 3, 4, 5, 6]
    assert nor["tyre"] == {"at": [0, 41], "v": ["SOFT", "HARD"]}
    assert nor["age"] == {"at": [0, 21, 41, 61, 81], "v": [0, 1, 0, 1, 2]}
    assert lec["tyre"]["v"] == ["SOFT"]


def test_pit_flag_window_uses_lane_duration(client, race):
    _, body = fetch(client)
    ver, nor, _lec = body["frames"]["drivers"]
    # pit entry t = 190, lane 22 s: inside [190, 212); frame 38 = 190 s, frame 43 = 215 s
    assert nor["pit"] == {"at": [0, 38, 43], "v": [0, 1, 0]}
    flags = expand(nor["pit"], 102)
    assert flags[37] == 0 and flags[38] == 1 and flags[42] == 1 and flags[43] == 0
    assert ver["pit"] == {"at": [0], "v": [0]}


def test_event_markers(client, race):
    _, body = fetch(client)
    events = body["events"]
    by_kind = {e["kind"]: e for e in events}
    assert [e["kind"] for e in events] == ["start", "safety_car", "pit", "red_flag", "chequered"]
    assert (by_kind["start"]["t"], by_kind["start"]["lap"]) == (0.0, 1)
    sc = by_kind["safety_car"]
    assert (sc["t"], sc["lap"], sc["end_t"], sc["end_lap"]) == (150.0, 2, 260.0, 3)
    pit = by_kind["pit"]
    assert (pit["t"], pit["lap"], pit["driver"]) == (190.0, 2, "NOR")
    assert (by_kind["red_flag"]["t"], by_kind["red_flag"]["lap"]) == (320.0, 4)
    # the leader (VER) completes lap 5 at 500 s
    assert (by_kind["chequered"]["t"], by_kind["chequered"]["lap"]) == (500.0, 5)


def test_vsc_without_end_lasts_to_the_end(client, race):
    add_rcm(race, at(350), "VIRTUAL SAFETY CAR DEPLOYED", lap=4)
    _, body = fetch(client)
    vsc = [e for e in body["events"] if e["kind"] == "vsc"][0]
    assert (vsc["t"], vsc["end_t"], vsc["end_lap"]) == (350.0, 505.0, 5)


def test_step_parameter(client, race):
    _, body = fetch(client, step=30)
    assert body["frames"]["count"] == 17 and body["frames"]["t"][:3] == [0, 30, 60]
    _, body = fetch(client, step=1)
    assert body["frames"]["count"] == 506
    for bad in ("0", "31", "abc", "-5", "2.5"):
        assert client.get(replay_url(), {"step": bad}).status_code == 400
    assert client.get(replay_url(), {"session": "Q"}).status_code == 400


def test_cache_header_only_for_finished_sessions(client, race):
    response, _ = fetch(client)
    assert "max-age=300" in response["Cache-Control"] and "public" in response["Cache-Control"]
    race.status = "live"
    race.save(update_fields=["status"])
    response, _ = fetch(client)
    assert "max-age=300" not in response.get("Cache-Control", "")


def test_missing_analytics_gives_404(client):
    assert client.get(replay_url(2024, 9)).status_code == 404
    old = make_session(year=2019, number=3)
    add_driver(old, "HAM", 1)
    response = client.get(replay_url(2019, 3))
    assert response.status_code == 404
    assert response.json()["analytics_available"] is False
    assert "2023" in response.json()["detail"]
    make_session(year=2024, number=5)  # session without any imported rows
    response = client.get(replay_url(2024, 5))
    assert response.status_code == 404
    assert response.json()["analytics_available"] is True
    assert client.get(replay_url(2024, 5), {"session": "SPRINT"}).status_code == 404


def test_sprint_session(client):
    sprint = make_session(type="SPRINT", status="finished")
    driver = add_driver(sprint, "VER", 1)
    add_laps(sprint, driver, [60_000] * 3)
    response = client.get(replay_url(), {"session": "SPRINT"})
    assert response.status_code == 200
    assert response.json()["session"]["type"] == "SPRINT"


def test_jump_to_lap_offsets(client, race):
    response = client.get("/api/v1/rounds/2024/1/replay/laps/")
    assert response.status_code == 200
    body = response.json()
    assert body["total_laps"] == 5 and body["duration_s"] == 505.0
    assert body["laps"] == [{"lap": n, "t": 100.0 * (n - 1)} for n in range(1, 6)]
    assert "max-age=300" in response["Cache-Control"]
    assert client.get("/api/v1/rounds/2024/9/replay/laps/").status_code == 404


def test_query_count_is_fixed(client, race):
    with CaptureQueriesContext(connection) as queries:
        assert client.get(replay_url()).status_code == 200
    assert len(queries) <= QUERY_CAP


def test_carry_forward_helper_is_a_merge():
    assert replay._carry([1.0, 3.0], ["a", "b"], [0.0, 1.0, 2.0, 3.0, 9.0]) == [
        None,
        "a",
        "a",
        "b",
        "b",
    ]
    assert replay._runs([0, 0, 1, 1, 0]) == {"at": [0, 2, 4], "v": [0, 1, 0]}


# --- Size and speed on a 2 hour race ---------------------------------------------------------


def build_long_race(drivers=20, lap_s=90, race_s=7200, samples=1000):
    """~25k rows: 20 drivers x (80 laps, 1000 interval samples, 150 position samples)."""
    session = make_session(status="results_final")
    laps_n = race_s // lap_s
    laps, positions, intervals, stints, pits = [], [], [], [], []
    for index in range(drivers):
        driver = add_driver(session, f"D{index:02d}", index + 1)
        base = index * 0.4
        laps.extend(
            Lap(
                session=session,
                driver=driver,
                lap_number=n,
                duration_ms=lap_s * 1000 + index,
                date_start=at(base + (n - 1) * lap_s),
            )
            for n in range(1, laps_n + 1)
        )
        positions.extend(
            PositionSample(
                session=session,
                driver=driver,
                ts=at(k * race_s / 150),
                position=(index + k) % drivers + 1,
            )
            for k in range(150)
        )
        intervals.extend(
            IntervalSample(
                session=session,
                driver=driver,
                ts=at(k * race_s / samples),
                gap_to_leader_ms=100_000 + index * 7_919 + k * 37,  # six digit worst case
                interval_ms=10_000 + (k * 211) % 9_000,
            )
            for k in range(samples)
        )
        stints += [
            stint(session, driver, 1, "MEDIUM", 1, 40),
            stint(session, driver, 2, "HARD", 41, laps_n),
        ]
        pits.append(
            PitStop(session=session, driver=driver, date=at(3600 + index * 3), lane_ms=21_000)
        )
    Lap.objects.bulk_create(laps, batch_size=5000)
    PositionSample.objects.bulk_create(positions, batch_size=5000)
    IntervalSample.objects.bulk_create(intervals, batch_size=5000)
    Stint.objects.bulk_create(stints)
    PitStop.objects.bulk_create(pits)
    return session


def test_two_hour_race_payload_is_small_and_fast(client):
    build_long_race()
    total_rows = (
        Lap.objects.count() + PositionSample.objects.count() + IntervalSample.objects.count()
    )
    assert 20_000 <= total_rows <= 30_000
    client.get(replay_url())  # warm up imports and plans
    with CaptureQueriesContext(connection) as queries:
        started = time.perf_counter()
        response = client.get(replay_url())
        elapsed = time.perf_counter() - started
    assert response.status_code == 200
    size = len(response.content)
    body = json.loads(response.content)
    assert body["frames"]["count"] >= 1440
    assert len(body["drivers"]) == 20
    print(f"payload={size} bytes, elapsed={elapsed:.3f}s, queries={len(queries)}")
    assert size < 600_000
    assert elapsed < 1.0
    assert len(queries) <= QUERY_CAP

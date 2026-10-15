import statistics
from datetime import UTC, datetime, timedelta

import pytest

from apps.analytics import selectors
from apps.analytics.models import (
    Lap,
    PitStop,
    PositionSample,
    RaceControlMessage,
    Stint,
    WeatherSample,
)
from apps.catalog import lookups
from apps.catalog.models import Session
from tests.catalog import factories as f

pytestmark = pytest.mark.django_db

T0 = datetime(2024, 3, 2, 15, 0, tzinfo=UTC)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


# --- Builders (shared with test_api) ---------------------------------------------------------


def make_session(year=2024, number=1, type=Session.Type.RACE, status="results_final"):
    season = f.SeasonFactory._meta.model.objects.filter(year=year).first() or f.SeasonFactory(
        year=year
    )
    rnd = f.RoundFactory(season=season, round=number, name=f"Round {number}")
    return f.SessionFactory(round=rnd, type=type, status=status)


def add_driver(session, code, position, constructor=None, color="#112233"):
    constructor = constructor or f.ConstructorFactory(name=f"Team {code}")
    if color is not False:
        f.ConstructorSeasonFactory(
            constructor=constructor, season=session.round.season, color_hex=color
        )
    driver = f.DriverFactory(code=code, given_name=code.title(), family_name="Driver")
    f.ResultFactory(session=session, driver=driver, constructor=constructor, position=position)
    return driver


def add_laps(session, driver, durations, start=0.0, pit_out=(), sectors=None):
    """Consecutive laps; a None duration leaves the next lap's start as the only end marker."""
    clock = start
    rows = []
    for number, duration in enumerate(durations, start=1):
        rows.append(
            Lap(
                session=session,
                driver=driver,
                lap_number=number,
                duration_ms=duration,
                date_start=at(clock),
                is_pit_out_lap=number in pit_out,
                sector1_ms=sectors[0] if sectors and duration else None,
                sector2_ms=sectors[1] if sectors and duration else None,
                sector3_ms=sectors[2] if sectors and duration else None,
            )
        )
        clock += (duration or 90_000) / 1000
    Lap.objects.bulk_create(rows)


def add_samples(session, driver, samples):
    PositionSample.objects.bulk_create(
        PositionSample(session=session, driver=driver, ts=at(s), position=p) for s, p in samples
    )


def add_rcm(session, ts, message, category="SafetyCar", lap=None, **kwargs):
    return RaceControlMessage.objects.create(
        session=session, ts=ts, message=message, category=category, lap_number=lap, **kwargs
    )


# --- catalog lookups -------------------------------------------------------------------------


def test_session_header_and_drivers_with_colours():
    session = make_session(status="finished")
    add_driver(session, "VER", 1, color="#3671c6")
    add_driver(session, "NOR", 2, color=False)  # no ConstructorSeason: neutral colour
    other = f.ResultFactory(
        session=session, driver=f.DriverFactory(code="", family_name="Zed"), position=None
    )

    header = lookups.get_session_header(2024, 1, "RACE")
    assert header is not None and header.is_final
    assert (header.year, header.round, header.round_name) == (2024, 1, "Round 1")
    assert lookups.get_session_header(2024, 1, "SPRINT") is None
    assert lookups.get_session_header(2024, 9, "RACE") is None

    drivers = lookups.session_drivers(session.id, "RACE")
    assert [d.code for d in drivers] == ["VER", "NOR", "ZED"]
    assert drivers[0].color_hex == "#3671c6"
    assert drivers[1].color_hex is None
    assert drivers[0].full_name == "Ver Driver"
    assert drivers[2].position is None and drivers[2].driver_id == other.driver_id


def test_session_drivers_use_qualifying_results_for_q():
    session = make_session(type=Session.Type.Q)
    f.QualifyingResultFactory(session=session, driver=f.DriverFactory(code="LEC"), position=1)
    assert [d.code for d in lookups.session_drivers(session.id, "Q")] == ["LEC"]


def test_header_is_final_only_when_finished():
    assert not lookups.SessionHeader(1, 2024, 1, "x", "RACE", "live").is_final
    assert lookups.SessionHeader(1, 2024, 1, "x", "RACE", "results_final").is_final


# --- positions -------------------------------------------------------------------------------


def hand_built_race():
    """Three drivers, three laps of 90 s; lap n ends at T0 + 90 n.

    A pits in lap 2 (drops to P3, recovers), B has no duration for lap 1 (its end is the start
    of lap 2), C retires during lap 2 (no end for lap 2, no lap 3).
    A sample exactly at a lap end counts for that lap.
    """
    session = make_session()
    a = add_driver(session, "AAA", 1)
    b = add_driver(session, "BBB", 2)
    c = add_driver(session, "CCC", 3)
    add_laps(session, a, [90_000] * 3)
    add_laps(session, b, [None, 90_000, 90_000])
    add_laps(session, c, [90_000, None])
    add_samples(session, a, [(-600, 1), (100, 3), (200, 2), (270, 1)])
    add_samples(session, b, [(-600, 2), (95, 1), (250, 2)])
    add_samples(session, c, [(-600, 3), (60, 2), (150, 19)])
    PitStop.objects.create(session=session, driver=a, date=at(120), lap_number=2)
    return session, a, b, c


def test_positions_per_lap_with_pit_stop_and_retirement():
    session, *_ = hand_built_race()
    header = lookups.get_session_header(2024, 1, "RACE")
    result = selectors.positions(header)
    by_code = {d["code"]: d for d in result["drivers"]}

    assert result["laps"] == [1, 2, 3]
    assert by_code["AAA"]["positions"] == [1, 3, 1]
    assert by_code["BBB"]["positions"] == [2, 1, 2]
    assert by_code["CCC"]["positions"] == [2, None, None]
    assert by_code["AAA"]["pit_laps"] == [2]
    assert by_code["BBB"]["pit_laps"] == []
    assert by_code["AAA"]["color_hex"] == "#112233"
    assert [d["code"] for d in result["drivers"]] == ["AAA", "BBB", "CCC"]


def test_positions_pit_lap_is_derived_from_time_when_lap_number_missing():
    session, a, *_ = hand_built_race()
    PitStop.objects.filter(driver=a).update(lap_number=None, date=at(100))
    header = lookups.get_session_header(2024, 1, "RACE")
    by_code = {d["code"]: d for d in selectors.positions(header)["drivers"]}
    assert by_code["AAA"]["pit_laps"] == [2]


def test_positions_without_laps_is_not_found():
    session = make_session()
    add_driver(session, "AAA", 1)
    header = lookups.get_session_header(2024, 1, "RACE")
    with pytest.raises(selectors.AnalyticsNotFound):
        selectors.positions(header)


# --- SC / VSC periods ------------------------------------------------------------------------


def test_neutralisations_from_messages():
    session, *_ = hand_built_race()
    add_rcm(session, at(100), "SAFETY CAR DEPLOYED", lap=2)
    add_rcm(session, at(170), "SAFETY CAR IN THIS LAP", lap=3)
    # No lap_number: derived from the time (lap 1 starts at T0).
    add_rcm(session, at(10), "VIRTUAL SAFETY CAR DEPLOYED")
    add_rcm(session, at(80), "VIRTUAL SAFETY CAR ENDING")
    add_rcm(session, at(5), "GREEN LIGHT - PIT EXIT OPEN", category="Flag")
    header = lookups.get_session_header(2024, 1, "RACE")
    assert selectors.positions(header)["neutralisations"] == [
        {"kind": "VSC", "start_lap": 1, "end_lap": 1},
        {"kind": "SC", "start_lap": 2, "end_lap": 3},
    ]


def test_a_virtual_safety_car_that_becomes_a_safety_car_ends_there():
    session, *_ = hand_built_race()
    add_rcm(session, at(10), "VIRTUAL SAFETY CAR DEPLOYED", lap=1)
    add_rcm(session, at(100), "SAFETY CAR DEPLOYED", lap=2)
    add_rcm(session, at(170), "SAFETY CAR IN THIS LAP", lap=3)
    header = lookups.get_session_header(2024, 1, "RACE")
    assert selectors.positions(header)["neutralisations"] == [
        {"kind": "VSC", "start_lap": 1, "end_lap": 2},
        {"kind": "SC", "start_lap": 2, "end_lap": 3},
    ]


def test_unclosed_period_lasts_until_last_lap():
    session, *_ = hand_built_race()
    add_rcm(session, at(100), "SAFETY CAR DEPLOYED", lap=2)
    header = lookups.get_session_header(2024, 1, "RACE")
    assert selectors.positions(header)["neutralisations"] == [
        {"kind": "SC", "start_lap": 2, "end_lap": 3}
    ]


# --- laps ------------------------------------------------------------------------------------


def slow_laps_race():
    session = make_session()
    d = add_driver(session, "AAA", 1)
    # Lap 1 pit-out, 2 fast, 3 in lap (pit stop), 4 pit-out, 5 under SC, 6 fast, 7 unfinished.
    durations = [100_000, 90_000, 95_000, 120_000, 130_000, 92_000, None]
    add_laps(session, d, durations, pit_out=(1, 4), sectors=(30_000, 30_000, 30_000))
    PitStop.objects.create(session=session, driver=d, date=at(300), lap_number=3)
    add_rcm(session, at(0), "SAFETY CAR DEPLOYED", lap=5)
    add_rcm(session, at(1), "SAFETY CAR IN THIS LAP", lap=5)
    return lookups.get_session_header(2024, 1, "RACE")


def test_laps_hide_slow_removes_out_in_and_neutralised_laps():
    header = slow_laps_race()
    driver = selectors.laps(header, [], hide_slow=True)["drivers"][0]
    assert driver["lap_numbers"] == [2, 6]
    assert driver["duration_ms"] == [90_000, 92_000]
    assert driver["sector1_ms"] == [30_000, 30_000]


def test_laps_without_hiding_keeps_everything_with_a_time():
    header = slow_laps_race()
    result = selectors.laps(header, [], hide_slow=False)
    assert result["drivers"][0]["lap_numbers"] == [1, 2, 3, 4, 5, 6]
    assert result["neutralisations"] == [{"kind": "SC", "start_lap": 5, "end_lap": 5}]


def test_laps_summary_median_and_stdev():
    session = make_session()
    d = add_driver(session, "AAA", 1)
    times = [90_000, 91_000, 92_000, 93_000]
    add_laps(session, d, [95_000, *times], pit_out=(1,))
    header = lookups.get_session_header(2024, 1, "RACE")
    summary = selectors.laps(header, [], hide_slow=True)["drivers"][0]["summary"]
    assert summary["count"] == 4
    assert summary["best_ms"] == 90_000
    assert summary["median_ms"] == 91_500.0
    assert summary["stdev_ms"] == round(statistics.stdev(times), 1)


def test_laps_summary_single_lap_has_no_stdev():
    session = make_session()
    add_laps(session, add_driver(session, "AAA", 1), [90_000])
    header = lookups.get_session_header(2024, 1, "RACE")
    summary = selectors.laps(header, [], hide_slow=False)["drivers"][0]["summary"]
    assert summary["stdev_ms"] is None and summary["best_ms"] == 90_000


def test_laps_filter_by_driver_codes():
    session = make_session()
    for position, code in enumerate(["VER", "NOR", "LEC"], start=1):
        add_laps(session, add_driver(session, code, position), [90_000, 91_000])
    header = lookups.get_session_header(2024, 1, "RACE")
    result = selectors.laps(header, ["nor", "VER"], hide_slow=False)
    assert [d["code"] for d in result["drivers"]] == ["VER", "NOR"]


# --- stints ----------------------------------------------------------------------------------


def make_stints(session, driver, rows):
    Stint.objects.bulk_create(
        Stint(
            session=session,
            driver=driver,
            stint_number=n,
            compound=compound,
            lap_start=start,
            lap_end=end,
            tyre_age_at_start=age,
        )
        for n, (compound, start, end, age) in enumerate(rows, start=1)
    )


def test_stints_in_result_order_with_letters_and_gaps_filled():
    session = make_session()
    first = add_driver(session, "AAA", 2)
    second = add_driver(session, "BBB", 1)
    make_stints(
        session, first, [("SOFT", 1, 20, 0), ("HARD", 21, None, 3), ("UNKNOWN", None, 0, 0)]
    )
    make_stints(session, second, [("INTERMEDIATE", 1, None, 0)])
    add_laps(session, first, [90_000] * 50)
    add_laps(session, second, [90_000] * 10)
    header = lookups.get_session_header(2024, 1, "RACE")
    result = selectors.stints(header)
    assert [d["code"] for d in result["drivers"]] == ["BBB", "AAA"]
    bbb, aaa = result["drivers"]
    assert bbb["stints"][0]["lap_end"] == 10 and bbb["stints"][0]["compound_letter"] == "I"
    assert [s["compound_letter"] for s in aaa["stints"]] == ["S", "H", "?"]
    assert aaa["stints"][0]["laps"] == 20
    assert aaa["stints"][1]["lap_end"] == 50 and aaa["stints"][1]["laps"] == 30
    assert aaa["stints"][1]["tyre_age_at_start"] == 3


# --- pit stops -------------------------------------------------------------------------------


def pit_session(with_stop_ms: bool):
    session = make_session()
    team_a, team_b = f.ConstructorFactory(name="Alpha"), f.ConstructorFactory(name="Beta")
    d1 = add_driver(session, "AAA", 1, constructor=team_a)
    d2 = add_driver(session, "BBB", 2, constructor=team_a, color=False)
    d3 = add_driver(session, "CCC", 3, constructor=team_b)
    make_stints(session, d1, [("MEDIUM", 1, 15, 0), ("HARD", 16, 40, 0)])
    make_stints(session, d3, [("SOFT", 1, 10, 0), ("MEDIUM", 11, 30, 0)])
    stop = (lambda v: v) if with_stop_ms else (lambda v: None)
    PitStop.objects.bulk_create(
        [
            PitStop(
                session=session,
                driver=d1,
                date=at(1),
                lap_number=15,
                stop_ms=stop(2400),
                lane_ms=21_000,
            ),
            PitStop(
                session=session,
                driver=d2,
                date=at(2),
                lap_number=12,
                stop_ms=stop(2100),
                lane_ms=22_500,
            ),
            PitStop(
                session=session,
                driver=d3,
                date=at(3),
                lap_number=10,
                stop_ms=stop(2900),
                lane_ms=20_500,
            ),
        ]
    )
    return lookups.get_session_header(2024, 1, "RACE")


def test_pit_stops_ranked_by_stop_duration_when_available():
    result = selectors.pit_stops(pit_session(with_stop_ms=True))
    assert result["method"] == "stop_duration"
    assert [(r["rank"], r["driver_code"], r["duration_ms"]) for r in result["ranking"]] == [
        (1, "BBB", 2100),
        (2, "CCC", 2900),
    ]


def test_pit_stops_fall_back_to_lane_duration():
    result = selectors.pit_stops(pit_session(with_stop_ms=False))
    assert result["method"] == "lane_duration"
    assert [(r["rank"], r["driver_code"], r["duration_ms"]) for r in result["ranking"]] == [
        (1, "CCC", 20_500),
        (2, "AAA", 21_000),
    ]


def test_pit_stop_table_has_compound_change_and_final_order():
    stops = selectors.pit_stops(pit_session(with_stop_ms=True))["stops"]
    assert [s["driver_code"] for s in stops] == ["AAA", "BBB", "CCC"]
    assert (stops[0]["compound_from"], stops[0]["compound_to"]) == ("MEDIUM", "HARD")
    assert (stops[1]["compound_from"], stops[1]["compound_to"]) == (None, None)
    assert (stops[2]["compound_from"], stops[2]["compound_to"]) == ("SOFT", "MEDIUM")
    assert stops[0]["lane_ms"] == 21_000 and stops[0]["stop_ms"] == 2400


# --- weather / race control ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("count", "expected"), [(0, 0), (5, 5), (120, 120), (121, 120), (5000, 120)]
)
def test_downsample_indices(count, expected):
    indices = selectors.downsample_indices(count, 120)
    assert len(indices) == expected
    assert indices == sorted(set(indices))
    if count > 1:
        assert indices[0] == 0 and indices[-1] == count - 1


def test_weather_is_downsampled():
    session = make_session()
    WeatherSample.objects.bulk_create(
        WeatherSample(session=session, ts=at(i * 60), air_temperature=20 + i / 100)
        for i in range(300)
    )
    result = selectors.weather(lookups.get_session_header(2024, 1, "RACE"))
    assert result["total_samples"] == 300
    assert len(result["samples"]) == 120
    assert result["samples"][0]["ts"] == at(0) and result["samples"][-1]["ts"] == at(299 * 60)


def test_race_control_filter_and_driver_code():
    session = make_session()
    driver = f.DriverFactory(code="HAM")
    add_rcm(session, at(1), "GREEN LIGHT", category="Flag", flag="GREEN")
    add_rcm(session, at(2), "5 SECOND TIME PENALTY", category="Other", driver=driver)
    add_rcm(session, at(3), "SAFETY CAR DEPLOYED")
    header = lookups.get_session_header(2024, 1, "RACE")
    everything = selectors.race_control(header, None)
    assert everything["categories"] == ["Flag", "Other", "SafetyCar"]
    assert [m["message"] for m in everything["messages"]][0] == "GREEN LIGHT"
    only = selectors.race_control(header, "other")
    assert [m["driver_code"] for m in only["messages"]] == ["HAM"]
    assert selectors.race_control(header, "Drs")["messages"] == []


# --- not found -------------------------------------------------------------------------------


@pytest.mark.parametrize("year", [2022, 2010])
def test_old_seasons_say_analytics_start_in_2023(year):
    session = make_session(year=year)
    header = lookups.get_session_header(year, 1, "RACE")
    for call in (selectors.stints, selectors.weather, selectors.pit_stops):
        with pytest.raises(selectors.AnalyticsNotFound) as error:
            call(header)
        assert error.value.message == "Detailed analytics are available from the 2023 season"
        assert error.value.analytics_available is False
    assert session.round.season.year == year


def test_missing_round_in_2024_is_a_plain_not_found():
    with pytest.raises(selectors.AnalyticsNotFound) as error:
        selectors.load_header(2024, 7, "RACE")
    assert error.value.analytics_available is True
    assert "not found" in error.value.message

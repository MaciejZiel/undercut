import datetime as dt
from decimal import Decimal

from apps.ingestion.jolpica import api_mapper as m

from . import data as d


def test_schedule_maps_sessions_with_assumed_end_times():
    [bahrain] = m.parse_schedule(d.schedule(d.BAHRAIN))

    assert (bahrain.round.year, bahrain.round.round, bahrain.round.name) == (
        2024,
        1,
        "Bahrain Grand Prix",
    )
    assert bahrain.circuit.jolpica_id == "bahrain" and bahrain.circuit.country == "Bahrain"
    by_type = {s.type: s for s in bahrain.sessions}
    assert set(by_type) == {"FP1", "FP2", "FP3", "Q", "RACE"}
    q = by_type["Q"]
    assert q.start_utc == dt.datetime(2024, 3, 1, 16, 0, tzinfo=dt.UTC)
    assert q.end_utc == dt.datetime(2024, 3, 1, 17, 0, tzinfo=dt.UTC)
    assert by_type["RACE"].end_utc - by_type["RACE"].start_utc == dt.timedelta(hours=2)
    # status is left alone so a calendar refresh can never downgrade a finished session
    assert all(s.status is None for s in bahrain.sessions)


def test_sprint_weekend_names_sprint_qualifying_as_sq():
    [china] = m.parse_schedule(d.schedule(d.CHINA))
    assert {s.type for s in china.sessions} == {"FP1", "SQ", "SPRINT", "Q", "RACE"}


def test_missing_times_become_unknown_not_midnight():
    race = d.race(2, "X Grand Prix", d.circuit(), "2024-03-09", time=None)
    race.pop("time")
    [parsed] = m.parse_schedule(d.schedule(race))
    assert parsed.sessions[-1].type == "RACE" and parsed.sessions[-1].start_utc is None
    assert parsed.sessions[-1].end_utc is None


def test_race_results_convert_strings_and_keep_race_day_constructor():
    parsed = m.parse_race_results(
        d.results(
            d.result_row(1, "1", d.VER, d.RED_BULL, 26, rank=1),
            d.result_row(2, "R", d.PER, d.RED_BULL, 0, status="Retired", millis=None, grid="3"),
        )
    )
    winner, retired = parsed.rows
    assert (winner.position, winner.position_text, winner.points) == (1, "1", Decimal(26))
    assert (winner.time_ms, winner.best_lap_ms, winner.fastest_lap_rank) == (5504742, 92608, 1)
    assert (retired.position_text, retired.status, retired.time_ms) == ("R", "Retired", None)
    assert retired.constructor_jolpica_id == "red_bull"
    assert set(parsed.drivers) == {"max_verstappen", "perez"}
    assert parsed.drivers["perez"].permanent_number == 11
    assert parsed.drivers["perez"].dob == dt.date(1990, 1, 26)


def test_sprint_uses_its_own_key():
    parsed = m.parse_race_results(
        d.results(d.result_row(1, "1", d.VER, d.RED_BULL, 8), key="SprintResults"), "SprintResults"
    )
    assert len(parsed.rows) == 1


def test_qualifying_keeps_missing_stages_empty():
    parsed = m.parse_qualifying(
        d.qualifying(
            d.quali_row(1, d.VER, d.RED_BULL, "1:30.031", "1:29.374", "1:29.179"),
            d.quali_row(20, d.SAI, d.FERRARI, "1:32.500"),
        )
    )
    pole, last = parsed.rows
    assert (pole.q1_ms, pole.q2_ms, pole.q3_ms) == (90031, 89374, 89179)
    assert (last.q1_ms, last.q2_ms, last.q3_ms) == (92500, None, None)


def test_duplicate_positions_are_made_unique():
    parsed = m.parse_race_results(
        d.results(
            d.result_row(1, "1", d.VER, d.RED_BULL, 25),
            d.result_row(1, "1", d.PER, d.RED_BULL, 0),
        )
    )
    assert [r.position for r in parsed.rows] == [1, None]


def test_standings_parse_points_wins_and_entities():
    drivers, _ = m.parse_standings(d.driver_standings((1, "26", 1, d.VER), (2, "18.5", 0, d.PER)))
    assert [(x.jolpica_id, x.position, x.points, x.wins) for x in drivers] == [
        ("max_verstappen", 1, Decimal(26), 1),
        ("perez", 2, Decimal("18.5"), 0),
    ]
    _, teams = m.parse_standings(d.constructor_standings((1, "44", 1, d.RED_BULL)))
    assert teams[0].constructor.name == "Red Bull"


def test_empty_standings_give_empty_lists():
    assert m.parse_standings({"StandingsTable": {"StandingsLists": []}}) == ([], [])

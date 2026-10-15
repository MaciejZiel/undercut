import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from apps.catalog.services import ResultData
from apps.ingestion.jolpica import mapper
from apps.ingestion.jolpica.dump import SessionEntryRow, read_dump

FIXTURES = Path(__file__).parent / "fixtures" / "dump"
TODAY = dt.date(2024, 1, 1)


@pytest.fixture(scope="module")
def dump():
    return read_dump(FIXTURES)


def bundle_for(dump, name_year, number):
    years = mapper.season_years(dump, None, None)
    for row in dump.rounds:
        if years[row.season_id] == name_year and row.number == number:
            return mapper.map_round(dump, row, years, today=TODAY)
    raise AssertionError("round not found")


def entry(**kw):
    base = dict(
        id=1,
        session_id=1,
        round_entry_id=1,
        position=1,
        grid=1,
        laps_completed=50,
        points="0",
        status="0",
        detail="Finished",
        time="",
        is_classified=True,
        fastest_lap_rank=None,
    )
    return SessionEntryRow(**{**base, **kw})


@pytest.mark.parametrize(
    ("text", "ms"),
    [
        ("02:13:23.6", 8003600),
        ("00:01:16.29", 76290),
        ("1:32.608", 92608),
        ("00:00:24.036", 24036),
        ("", None),
        ("abc", None),
    ],
)
def test_parse_interval_ms(text, ms):
    assert mapper.parse_interval_ms(text) == ms


def test_position_text():
    assert mapper.position_text(entry()) == "1"
    assert mapper.position_text(entry(is_classified=False, status="11", detail="Engine")) == "R"
    assert mapper.position_text(entry(is_classified=False, status="20", detail="DSQ")) == "D"
    assert mapper.position_text(entry(is_classified=False, status="30", detail="Withdrew")) == "W"
    assert (
        mapper.position_text(entry(is_classified=False, status="1", detail="Not classified")) == "N"
    )
    assert mapper.position_text(entry(detail="", status="", is_classified=False)) == "1"


def test_normalise_color():
    assert mapper.normalise_color("3671C6") == "#3671c6"
    assert mapper.normalise_color("#E80020") == "#e80020"
    assert mapper.normalise_color("") is None
    assert mapper.normalise_color("red") is None


def test_session_types_cover_sprint_qualifying():
    assert mapper.SESSION_TYPES["SQ2"] == "SQ"
    assert mapper.SESSION_TYPES["SR"] == "SPRINT"
    assert mapper.SESSION_TYPES["QB"] == "Q"


def test_qualifying_laps_are_merged_into_q1_q2_q3(dump):
    bundle = bundle_for(dump, 2023, 1)
    quali = next(s for s in bundle.sessions if s.session.type == "Q")
    by_driver = {r.driver_jolpica_id: r for r in quali.qualifying}
    ver, lec, ham = (by_driver[k] for k in ("max_verstappen", "leclerc", "hamilton"))
    assert (ver.q1_ms, ver.q2_ms, ver.q3_ms) == (72900, 72500, 71400)
    assert (lec.q1_ms, lec.q2_ms, lec.q3_ms) == (73200, 72700, 71365)
    assert (ham.q1_ms, ham.q2_ms, ham.q3_ms) == (73400, 72800, None)  # out in Q2
    assert [r.position for r in quali.qualifying] == [1, 2, 3]
    assert quali.qualifying[0].driver_jolpica_id == "leclerc"  # pole from the Q3 position


def test_sprint_weekend_has_sprint_and_sprint_qualifying(dump):
    bundle = bundle_for(dump, 2023, 1)
    types = [s.session.type for s in bundle.sessions]
    assert types == ["Q", "RACE", "SPRINT", "SQ"]  # FP1 has no data and the round is past
    sprint = next(s for s in bundle.sessions if s.session.type == "SPRINT")
    assert [r.position_text for r in sprint.results] == ["1", "D"]
    sq = next(s for s in bundle.sessions if s.session.type == "SQ")
    assert sq.qualifying[0].driver_jolpica_id == "hamilton"
    assert sq.qualifying[0].q3_ms == 72900


def test_team_is_the_one_on_race_day(dump):
    ham_2022 = next(
        r for r in bundle_for(dump, 2022, 1).sessions[1].results if "ham" in r.driver_jolpica_id
    )
    race_2023 = next(s for s in bundle_for(dump, 2023, 1).sessions if s.session.type == "RACE")
    ham_2023 = next(r for r in race_2023.results if r.driver_jolpica_id == "hamilton")
    assert ham_2022.constructor_jolpica_id == "mercedes"
    assert ham_2023.constructor_jolpica_id == "ferrari"


def test_race_result_values(dump):
    race = next(s for s in bundle_for(dump, 2022, 1).sessions if s.session.type == "RACE")
    ver, ham, lec = race.results
    assert (ver.position, ver.position_text, ver.time_ms, ver.points) == (
        1,
        "1",
        5400500,
        Decimal(25),
    )
    assert ver.fastest_lap_rank == 1 and ver.grid == 1
    assert (lec.position_text, lec.status, lec.laps) == ("R", "Engine", 30)
    assert race.session.status == "results_final"


def test_cancelled_round_has_no_number_and_no_sessions(dump):
    years = mapper.season_years(dump, None, None)
    row = next(r for r in dump.rounds if r.is_cancelled)
    bundle = mapper.map_round(dump, row, years, today=TODAY)
    assert bundle.round.round is None and bundle.round.is_cancelled
    assert bundle.sessions == ()


def test_midnight_timestamps_mean_unknown_start(dump):
    assert mapper._start_utc("1950-05-13 00:00:00+00:00") is None
    assert mapper._start_utc("2023-05-28 13:00:00+00:00") == dt.datetime(
        2023, 5, 28, 13, tzinfo=dt.UTC
    )


def test_deleted_laps_are_ignored(dump):
    assert "00:00:59.0" not in dump.fastest_laps.values()


def test_duplicate_positions_and_fastest_laps_are_made_unique():
    rows = [
        ResultData("a", "x", position=1, fastest_lap_rank=1),
        ResultData("b", "x", position=1, fastest_lap_rank=1),
    ]
    first, second = mapper._unique_positions(rows, rank_field="fastest_lap_rank")
    assert (first.position, first.fastest_lap_rank) == (1, 1)
    assert (second.position, second.fastest_lap_rank) == (None, None)


def test_circuit_timezone_comes_from_sessions(dump):
    circuits = {c.jolpica_id: c for c in mapper.map_circuits(dump, dump.rounds)}
    assert circuits["monaco"].timezone == "Europe/Monaco"
    assert circuits["jeddah"].timezone == ""


def test_constructor_season_colour(dump):
    years = mapper.season_years(dump, None, None)
    colours = {
        (c.constructor_jolpica_id, c.year): c.color_hex
        for c in mapper.map_constructor_seasons(dump, years)
    }
    assert colours[("red_bull", 2022)] == "#3671c6"
    assert colours[("mercedes", 2022)] is None

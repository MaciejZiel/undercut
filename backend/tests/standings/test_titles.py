"""Titles derived from standings, and the arithmetic of the title race (FR-305)."""

import datetime as dt
from decimal import Decimal

import pytest

from apps.standings import selectors
from apps.standings.selectors import Scoring, default_scoring, title_chances
from tests.catalog import factories as cf

from . import factories as f

D = Decimal
URL = "/api/v1/standings/title-race/"


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# --- Pure arithmetic -------------------------------------------------------------------------


def test_default_scoring_by_era():
    assert default_scoring(2024) == Scoring(25, True, 8)
    assert default_scoring(2025) == Scoring(25, False, 8)  # no fastest-lap point from 2025
    assert default_scoring(2018) == Scoring(25, False, 0)  # no sprints before 2021
    assert default_scoring(2021).sprint_win == 3
    assert default_scoring(2019).race_max == 26
    assert default_scoring(1995).race_win == 10
    assert default_scoring(1975).race_win == 9


def test_max_available_counts_races_sprints_and_fastest_lap():
    scoring = default_scoring(2024)  # 26 per race, 8 per sprint
    result = title_chances({1: D(10), 2: D(0)}, 3, 2, scoring)
    assert result["max_available"] == 3 * 26 + 2 * 8
    scoring = default_scoring(2025)  # 25 per race, no fastest-lap point
    assert title_chances({1: D(10), 2: D(0)}, 3, 2, scoring)["max_available"] == 75 + 16


def test_still_open_and_eliminated():
    points = {1: D(100), 2: D(80), 3: D(40)}
    result = title_chances(points, 2, 0, default_scoring(2025))  # 50 left for one driver
    assert result["drivers"][2]["max_points"] == 130
    assert result["drivers"][2]["can_win"] is True
    assert result["drivers"][3]["max_points"] == 90
    assert result["drivers"][3]["can_win"] is False
    assert result["champion"] is None


def test_decided_when_leader_beats_every_maximum():
    points = {1: D(200), 2: D(120), 3: D(60)}
    # 3 races x 25 = 75: second can reach 195 < 200.
    assert title_chances(points, 3, 0, default_scoring(2025))["champion"] == 1
    # The same gap is still open with the 2024 fastest-lap point? 120 + 3*26 = 198 < 200.
    assert title_chances(points, 3, 0, default_scoring(2024))["champion"] == 1
    # One more race (4 x 25 = 100) reopens it.
    assert title_chances(points, 4, 0, default_scoring(2025))["champion"] is None


def test_boundary_with_and_without_sprint():
    scoring = default_scoring(2025)
    # Gap 25: one race alone leaves a tie on points.
    tie = title_chances({1: D(100), 2: D(75)}, 1, 0, scoring)
    assert tie["champion"] is None
    assert tie["drivers"][2]["can_win"] is True
    assert tie["drivers"][2]["tie_break_needed"] is True
    # Gap 26: one race is not enough, the title is decided.
    assert title_chances({1: D(101), 2: D(75)}, 1, 0, scoring)["champion"] == 1
    # The same gap 26 with a sprint on top (25 + 8) is open again.
    open_ = title_chances({1: D(101), 2: D(75)}, 1, 1, scoring)
    assert open_["champion"] is None
    assert open_["drivers"][2]["tie_break_needed"] is False
    assert open_["drivers"][2]["max_points"] == 108


def test_equal_points_at_the_end_is_not_decided_by_arithmetic():
    result = title_chances({1: D(100), 2: D(100)}, 0, 0, default_scoring(2025))
    assert result["champion"] is None
    assert result["drivers"][1]["tie_break_needed"] is True
    assert result["drivers"][2]["tie_break_needed"] is True


def test_half_points_and_single_driver():
    result = title_chances({1: D("12.5"), 2: D("12")}, 0, 0, default_scoring(2025))
    assert result["champion"] == 1
    assert title_chances({1: D(5)}, 2, 0, default_scoring(2025))["champion"] == 1


# --- Titles from the tables ------------------------------------------------------------------


def season_with_rounds(year, rounds=2, race_results=True, sprint_rounds=(), cancelled_last=False):
    season = f.SeasonFactory(year=year)
    made = []
    for n in range(1, rounds + 1):
        rnd = cf.RoundFactory(season=season, round=n, date=dt.date(year, 3, n))
        race = cf.SessionFactory(round=rnd, type="RACE")
        if n in sprint_rounds:
            cf.SessionFactory(round=rnd, type="SPRINT")
        if race_results:
            cf.ResultFactory(session=race, position=1, driver=f.DriverFactory())
        made.append(rnd)
    if cancelled_last:
        cf.RoundFactory(season=season, round=None, is_cancelled=True, date=dt.date(year, 12, 1))
    return season, made


@pytest.mark.django_db
def test_champion_needs_position_one_after_last_round_with_results(django_assert_num_queries):
    s2000, _ = season_with_rounds(2000, rounds=2)
    champ, other = f.DriverFactory(), f.DriverFactory()
    f.DriverStandingFactory(season=s2000, after_round=1, driver=other, position=1)
    f.DriverStandingFactory(season=s2000, after_round=1, driver=champ, position=2)
    f.DriverStandingFactory(season=s2000, after_round=2, driver=champ, position=1)
    f.DriverStandingFactory(season=s2000, after_round=2, driver=other, position=2)
    # Season 2001: results only for round 1 of 2, so it is unfinished.
    s2001, rounds = season_with_rounds(2001, rounds=2)
    rounds[1].sessions.first().results.all().delete()
    f.DriverStandingFactory(season=s2001, after_round=1, driver=other, position=1)
    f.DriverStandingFactory(season=s2001, after_round=2, driver=other, position=1)
    # Season 2002 is finished but a cancelled round (no number) follows the last race.
    s2002, _ = season_with_rounds(2002, rounds=1, cancelled_last=True)
    f.DriverStandingFactory(season=s2002, after_round=1, driver=other, position=1)

    with django_assert_num_queries(2):
        assert selectors.champions("drivers") == {2000: champ.pk, 2002: other.pk}
    assert selectors.title_counts("drivers") == {champ.pk: 1, other.pk: 1}


@pytest.mark.django_db
def test_season_without_standings_for_last_round_is_not_finished():
    season, _ = season_with_rounds(2010, rounds=3)
    driver = f.DriverFactory()
    f.DriverStandingFactory(season=season, after_round=2, driver=driver, position=1)
    assert selectors.champions("drivers") == {}


@pytest.mark.django_db
def test_constructors_count_from_1958():
    team = f.ConstructorFactory()
    for year in (1957, 1958, 1959):
        season, _ = season_with_rounds(year, rounds=1)
        f.ConstructorStandingFactory(season=season, after_round=1, constructor=team, position=1)
    assert sorted(selectors.champions("constructors")) == [1958, 1959]
    assert selectors.title_counts("constructors") == {team.pk: 2}
    assert selectors.title_counts("drivers") == {}


@pytest.mark.django_db
def test_entity_summary_positions_and_titles_match_champions(django_assert_num_queries):
    season, _ = season_with_rounds(2020, rounds=2)
    a, b = f.DriverFactory(), f.DriverFactory()
    f.DriverStandingFactory(season=season, after_round=1, driver=a, position=1)
    f.DriverStandingFactory(season=season, after_round=2, driver=a, position=2)
    f.DriverStandingFactory(season=season, after_round=2, driver=b, position=1)
    # b leads the table of the finished season 2020 (it has race results).
    assert selectors.entity_summary("drivers", a.pk) == {"titles": 0, "positions": {2020: 2}}
    finished, _ = season_with_rounds(2021, rounds=1)
    f.DriverStandingFactory(season=finished, after_round=1, driver=b, position=1)
    f.DriverStandingFactory(season=finished, after_round=1, driver=a, position=2)
    f.ConstructorStandingFactory(season=finished, after_round=1, position=1)
    with django_assert_num_queries(1):
        summary = selectors.entity_summary("drivers", b.pk)
    assert summary == {"titles": 2, "positions": {2020: 1, 2021: 1}}
    assert selectors.entity_summary("drivers", a.pk)["titles"] == 0
    for driver in (a, b):
        assert selectors.entity_summary("drivers", driver.pk)["titles"] == selectors.title_counts(
            "drivers"
        ).get(driver.pk, 0)
    assert selectors.entity_summary("constructors", 0) == {"titles": 0, "positions": {}}


# --- Title race endpoint ---------------------------------------------------------------------


def table(season, after_round, rows):
    drivers = []
    for position, (points, wins) in enumerate(rows, start=1):
        driver = f.DriverFactory()
        drivers.append(driver)
        f.DriverStandingFactory(
            season=season,
            after_round=after_round,
            driver=driver,
            position=position,
            position_text=str(position),
            points=points,
            wins=wins,
        )
    return drivers


@pytest.mark.django_db
def test_title_race_ongoing_season_lists_contenders(client, django_assert_max_num_queries):
    season = f.SeasonFactory(year=2025)
    for n in range(1, 6):
        rnd = cf.RoundFactory(season=season, round=n, date=dt.date(2025, 3, n))
        cf.SessionFactory(round=rnd, type="RACE")
        if n == 5:
            cf.SessionFactory(round=rnd, type="SPRINT")
    cf.RoundFactory(season=season, round=None, is_cancelled=True, date=dt.date(2025, 12, 1))
    # After round 3: 2 races left, one with a sprint = 25 + 25 + 8 = 58 available.
    drivers = table(season, 3, [(100, 2), (80, 1), (45, 0), (30, 0)])
    with django_assert_max_num_queries(10):
        body = client.get(URL).json()
    assert body["season"] == 2025
    assert body["after_round"] == 3
    assert body["rounds_remaining"] == 2
    assert body["sprints_remaining"] == 1
    assert float(body["max_points_available"]) == 58
    assert body["fastest_lap_point"] is False
    assert body["decided"] is False
    assert body["message"] is None
    # 45 + 58 = 103 >= 100 stays in; 30 + 58 = 88 does not.
    assert [c["entity"]["id"] for c in body["contenders"]] == [d.pk for d in drivers[:3]]
    assert body["eliminated"] == 1
    assert float(body["contenders"][1]["max_points"]) == 138
    assert float(body["contenders"][1]["gap_to_leader"]) == 20


@pytest.mark.django_db
def test_title_race_decided_reports_the_round(client):
    season = f.SeasonFactory(year=2024)
    for n in range(1, 5):
        cf.RoundFactory(season=season, round=n, date=dt.date(2024, 3, n))
    # 2024 scoring: 26 per race. After R1: 60-40 with 3 races left (78) open. After R2: 126-60
    # with 2 left (52): 112 < 126, decided. R3 stays decided.
    leader, second = f.DriverFactory(), f.DriverFactory()
    for after_round, (a, b) in {1: (60, 40), 2: (126, 60), 3: (150, 80)}.items():
        f.DriverStandingFactory(season=season, after_round=after_round, driver=leader, points=a)
        f.DriverStandingFactory(
            season=season, after_round=after_round, driver=second, position=2, points=b
        )
    body = client.get(URL, {"season": 2024}).json()
    assert body["decided"] is True
    assert body["decided_in_round"] == 2
    assert body["message"] == "Champion decided in round 2"
    assert body["champion"]["id"] == leader.pk
    assert [c["entity"]["id"] for c in body["contenders"]] == [leader.pk]
    assert body["eliminated"] == 1
    assert body["fastest_lap_point"] is True


@pytest.mark.django_db
def test_title_race_level_points_after_last_round_uses_official_position(client):
    season = f.SeasonFactory(year=2025)
    cf.RoundFactory(season=season, round=1, date=dt.date(2025, 3, 1))
    first, second = f.DriverFactory(), f.DriverFactory()
    f.DriverStandingFactory(season=season, after_round=1, driver=first, points=50, position=1)
    f.DriverStandingFactory(season=season, after_round=1, driver=second, points=50, position=2)
    body = client.get(URL).json()
    assert body["decided"] is True
    assert body["champion"]["id"] == first.pk
    assert body["decided_in_round"] == 1


@pytest.mark.django_db
def test_title_race_empty_and_errors(client):
    body = client.get(URL).json()
    assert body["season"] is None
    assert body["contenders"] == []
    assert body["decided"] is False
    assert client.get(URL, {"season": 1999}).status_code == 404
    f.SeasonFactory(year=1999)
    assert client.get(URL, {"season": 1999}).json()["contenders"] == []
    assert client.get(URL, {"season": "x"}).status_code == 400
    assert client.post(URL).status_code in (401, 403, 405)

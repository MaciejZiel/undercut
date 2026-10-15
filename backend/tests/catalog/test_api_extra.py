"""Calendar, ICS, dashboard, titles, compare and season matrix."""

import datetime as dt

import pytest
from rest_framework.test import APIClient

from apps.catalog import selectors
from apps.catalog.api import compare as compare_api
from apps.catalog.api.calendar import build_ics, escape_text, fold_line
from apps.catalog.models import Session
from tests.standings import factories as sf

from . import factories as f

pytestmark = pytest.mark.django_db

RACE, SPRINT, QUALI = Session.Type.RACE, Session.Type.SPRINT, Session.Type.Q
UTC = dt.UTC


@pytest.fixture
def client():
    return APIClient()


def at(y, m, d, h=12, minute=0):
    return dt.datetime(y, m, d, h, minute, tzinfo=UTC)


def make_round(year, number, date, **kwargs):
    season = f.SeasonFactory._meta.model.objects.filter(year=year).first() or f.SeasonFactory(
        year=year
    )
    return f.RoundFactory(season=season, round=number, date=date, **kwargs)


def race_result(rnd, driver, team, session_type=RACE, **kwargs):
    session = Session.objects.filter(round=rnd, type=session_type).first() or f.SessionFactory(
        round=rnd, type=session_type
    )
    return f.ResultFactory(session=session, driver=driver, constructor=team, **kwargs)


# --- Calendar --------------------------------------------------------------------------------


def build_calendar_2030():
    circuit = f.CircuitFactory(name="Spa, Francorchamps", locality="Stavelot", country="Belgium")
    r1 = make_round(2030, 1, dt.date(2030, 3, 10), circuit=circuit, name="Alpha GP")
    r2 = make_round(2030, 2, dt.date(2030, 3, 24), name="Beta GP")
    r3 = make_round(2030, 3, dt.date(2030, 4, 7), name="Gamma GP")
    cancelled = make_round(2030, None, dt.date(2030, 4, 14), is_cancelled=True, name="Delta GP")
    race1 = f.SessionFactory(round=r1, type=RACE, start_utc=at(2030, 3, 10, 14))
    f.SessionFactory(round=r1, type=Session.Type.FP1, start_utc=at(2030, 3, 8, 11))
    f.SessionFactory(round=r1, type=SPRINT, start_utc=at(2030, 3, 9, 11))
    f.SessionFactory(round=r2, type=RACE, start_utc=at(2030, 3, 24, 14))
    f.SessionFactory(round=r3, type=RACE, start_utc=at(2030, 4, 7, 14))
    f.SessionFactory(round=cancelled, type=RACE, start_utc=at(2030, 4, 14, 14))
    winner = f.DriverFactory(given_name="Ada", family_name="Winner")
    team = f.ConstructorFactory(name="Red")
    f.ConstructorSeasonFactory(constructor=team, season=r1.season, color_hex="#ff0000")
    f.ResultFactory(session=race1, driver=winner, constructor=team, position=1)
    return r1, r2, r3


def test_calendar_statuses_and_next_flag(client):
    build_calendar_2030()
    body = selectors.calendar(2030, now=at(2030, 3, 15))
    assert [(r["round"], r["status"]) for r in body["rounds"]] == [
        (1, "completed"),
        (2, "next"),
        (3, "upcoming"),
        (None, "cancelled"),
    ]
    assert body["next_round"] == {
        "round": 2,
        "name": "Beta GP",
        "race_start_utc": at(2030, 3, 24, 14),
    }
    assert [r["is_next"] for r in body["rounds"]].count(True) == 1


def test_calendar_race_in_progress_is_next_and_started_race_without_data_is_completed():
    build_calendar_2030()
    # Race 2 started two hours ago: still the next round.
    body = selectors.calendar(2030, now=at(2030, 3, 24, 16))
    assert [r["status"] for r in body["rounds"] if r["round"]] == ["completed", "next", "upcoming"]
    # Five hours after the start it counts as completed even without results.
    body = selectors.calendar(2030, now=at(2030, 3, 24, 19))
    assert [r["status"] for r in body["rounds"] if r["round"]] == [
        "completed",
        "completed",
        "next",
    ]


def test_calendar_endpoint_shape_and_default_year(client):
    build_calendar_2030()
    make_round(2029, 1, dt.date(2029, 3, 1))
    body = client.get("/api/v1/calendar/").json()
    assert body["year"] == 2030
    first = body["rounds"][0]
    assert first["status"] == "completed"
    assert first["circuit"]["timezone"] == "Europe/Warsaw"
    assert first["has_sprint"] is True
    assert [s["type"] for s in first["sessions"]] == ["FP1", "SPRINT", "RACE"]
    assert first["winner"]["driver"]["name"] == "Ada Winner"
    assert first["winner"]["team"]["color"] == "#ff0000"
    assert first["race_start_utc"].startswith("2030-03-10T14:00:00")
    assert client.get("/api/v1/calendar/", {"year": 2029}).json()["year"] == 2029
    assert client.get("/api/v1/calendar/", {"year": 1980}).status_code == 404
    assert client.get("/api/v1/calendar/", {"year": "abc"}).status_code == 400


def test_calendar_empty_database(client):
    assert client.get("/api/v1/calendar/").json() == {
        "year": None,
        "next_round": None,
        "rounds": [],
    }
    assert client.get("/api/v1/calendar/ics/").status_code == 404


# --- iCalendar -------------------------------------------------------------------------------


def test_escape_text():
    assert escape_text("a,b;c\\d\ne") == r"a\,b\;c\\d\ne"


def test_fold_line_limits_octets_and_keeps_characters():
    assert fold_line("SHORT") == "SHORT"
    line = "SUMMARY:" + "Grand Prix, " * 20
    folded = fold_line(line)
    physical = folded.split("\r\n")
    assert all(len(p.encode()) <= 75 for p in physical)
    assert all(p.startswith(" ") for p in physical[1:])
    assert "".join([physical[0], *(p[1:] for p in physical[1:])]) == line
    accented = "DESCRIPTION:" + "Grand Prix de São Paulo ąęłó " * 8
    folded = fold_line(accented)
    assert all(len(p.encode()) <= 75 for p in folded.split("\r\n"))
    unfolded = folded.replace("\r\n ", "")
    assert unfolded == accented  # no character was split


def test_ics_endpoint_round_and_year(client):
    build_calendar_2030()
    response = client.get("/api/v1/calendar/ics/", {"year": 2030, "round": 1})
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    text = response.content.decode()
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert text.count("BEGIN:VEVENT") == 3
    assert "UID:2030-r1-RACE@undercut" in text
    assert "DTSTART:20300310T140000Z" in text
    assert "DTEND:20300310T160000Z" in text  # default two hours, end unknown
    assert "SUMMARY:Alpha GP - Race" in text
    assert "LOCATION:Spa\\, Francorchamps\\, Stavelot\\, Belgium" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    whole = client.get("/api/v1/calendar/ics/", {"year": 2030}).content.decode()
    assert whole.count("BEGIN:VEVENT") == 5  # cancelled round skipped
    uids = [line for line in whole.split("\r\n") if line.startswith("UID:")]
    assert len(uids) == len(set(uids))
    again = client.get("/api/v1/calendar/ics/", {"year": 2030}).content.decode()
    assert [x for x in again.split("\r\n") if x.startswith("UID:")] == uids
    assert client.get("/api/v1/calendar/ics/", {"year": 2030, "round": 9}).status_code == 404


def test_ics_skips_sessions_without_start_and_uses_end_when_known():
    rnd = make_round(2031, 1, dt.date(2031, 3, 1), name="Open GP")
    f.SessionFactory(round=rnd, type=RACE, start_utc=at(2031, 3, 1, 10), end_utc=at(2031, 3, 1, 11))
    f.SessionFactory(round=rnd, type=Session.Type.Q, start_utc=None)
    text = build_ics(selectors.calendar(2031, now=at(2031, 1, 1)), None, at(2031, 1, 1))
    assert text.count("BEGIN:VEVENT") == 1
    assert "DTEND:20310301T110000Z" in text
    assert "DTSTAMP:20310101T120000Z" in text


# --- Dashboard -------------------------------------------------------------------------------


def test_dashboard_empty_database(client):
    body = client.get("/api/v1/dashboard/").json()
    assert body["next_race"] is None
    assert body["last_race"] is None
    assert body["this_day_in_f1"] is None
    assert body["driver_standings"] == {"season": None, "after_round": None, "entries": []}
    assert body["constructor_standings"]["entries"] == []
    assert body["counts"] == {"seasons": 0, "races": 0, "drivers": 0}


def seed_dashboard():
    season = f.SeasonFactory(year=2024)
    r1 = f.RoundFactory(season=season, round=1, date=dt.date(2024, 3, 2), name="Opening GP")
    race = f.SessionFactory(round=r1, type=RACE, start_utc=at(2024, 3, 2, 15))
    teams = [f.ConstructorFactory(name=f"Team {n}") for n in range(3)]
    for team, colour in zip(teams, ["#111111", "#222222", None], strict=True):
        f.ConstructorSeasonFactory(constructor=team, season=season, color_hex=colour)
    drivers = [f.DriverFactory() for _ in range(7)]
    for position, driver in enumerate(drivers[:4], start=1):
        f.ResultFactory(
            session=race,
            driver=driver,
            constructor=teams[position % 3],
            position=position,
            fastest_lap_rank=1 if position == 4 else None,
            best_lap_ms=91234 if position == 4 else None,
        )
    future = f.RoundFactory(season=season, round=2, date=dt.date(2999, 1, 1), name="Future GP")
    f.SessionFactory(round=future, type=RACE, start_utc=at(2999, 1, 1, 14))
    for after_round in (1,):
        for position, driver in enumerate(drivers, start=1):
            sf.DriverStandingFactory(
                season=season,
                after_round=after_round,
                driver=driver,
                position=position,
                points=100 - position,
            )
        for position, team in enumerate(teams, start=1):
            sf.ConstructorStandingFactory(
                season=season, after_round=after_round, constructor=team, position=position
            )
    return drivers, teams


def test_dashboard_content(client):
    drivers, teams = seed_dashboard()
    body = client.get("/api/v1/dashboard/").json()
    assert body["next_race"]["name"] == "Future GP"
    assert body["next_race"]["year"] == 2024
    assert body["next_race"]["race_start_utc"].startswith("2999-01-01T14:00")
    last = body["last_race"]
    assert last["name"] == "Opening GP"
    assert [p["position"] for p in last["podium"]] == [1, 2, 3]
    assert last["podium"][0]["team"]["slug"] == teams[1].slug
    assert last["podium"][0]["team"]["color"] == "#222222"
    assert last["podium"][1]["team"]["color"] is None
    assert last["fastest_lap"]["driver"]["slug"] == drivers[3].slug
    assert last["fastest_lap"]["time_ms"] == 91234
    assert len(body["driver_standings"]["entries"]) == 5
    assert body["driver_standings"]["entries"][0]["slug"] == drivers[0].slug
    first, second, _, _, no_race = body["driver_standings"]["entries"]
    # A driver's colour is the colour of the team they raced for that season.
    assert (first["team_name"], first["color"]) == (teams[1].name, "#222222")
    assert (second["team_name"], second["color"]) == (teams[2].name, None)
    assert (no_race["team_name"], no_race["color"]) == (None, None)
    assert len(body["constructor_standings"]["entries"]) == 3
    assert body["constructor_standings"]["entries"][0]["color"] == "#111111"
    assert body["constructor_standings"]["entries"][0]["team_name"] is None
    assert body["counts"]["seasons"] == 1
    assert body["counts"]["races"] == 1  # the future round is not counted
    assert body["counts"]["drivers"] == 7


def test_dashboard_last_race_without_fastest_lap(client):
    rnd = make_round(2024, 1, dt.date(2024, 3, 2))
    race_result(rnd, f.DriverFactory(), f.ConstructorFactory(), position=1)
    body = client.get("/api/v1/dashboard/").json()
    assert body["last_race"]["fastest_lap"] is None
    assert len(body["last_race"]["podium"]) == 1


def test_this_day_in_f1_is_deterministic_and_from_an_earlier_year():
    team = f.ConstructorFactory()
    names = {}
    for year in (1990, 2000, 2010):
        rnd = make_round(year, 1, dt.date(year, 5, 5), name=f"GP {year}")
        driver = f.DriverFactory()
        race_result(rnd, driver, team, position=1)
        names[year] = rnd.name
    make_round(2020, 1, dt.date(2020, 5, 6))  # other day
    today = dt.date(2025, 5, 5)
    pick = selectors.this_day_in_f1(today)
    assert pick == selectors.this_day_in_f1(today)
    assert pick["race"] == names[(1990, 2000, 2010)[today.toordinal() % 3]]
    seen = {selectors.this_day_in_f1(dt.date(2025 + k, 5, 5))["year"] for k in range(1, 4)}
    assert seen <= {1990, 2000, 2010}
    assert selectors.this_day_in_f1(dt.date(2010, 5, 5))["year"] in {1990, 2000}
    assert selectors.this_day_in_f1(dt.date(1990, 5, 5)) is None  # never the same or a later year
    assert selectors.this_day_in_f1(dt.date(2025, 6, 6)) is None


# --- Titles ----------------------------------------------------------------------------------


def finished_season(year, champion, runner_up, champion_team=None):
    """A one-round season with results and final tables (champion first)."""
    rnd = make_round(year, 1, dt.date(year, 6, 1))
    team = champion_team or f.ConstructorFactory()
    race_result(rnd, champion, team, position=1)
    race_result(rnd, runner_up, team, position=2)
    sf.DriverStandingFactory(season=rnd.season, after_round=1, driver=champion, position=1)
    sf.DriverStandingFactory(season=rnd.season, after_round=1, driver=runner_up, position=2)
    sf.ConstructorStandingFactory(season=rnd.season, after_round=1, constructor=team, position=1)
    return rnd.season, team


def test_titles_in_lists_details_filter_and_seasons(client):
    ham, ver = f.DriverFactory(slug="ham"), f.DriverFactory(slug="ver")
    nobody = f.DriverFactory(slug="nobody")
    team = f.ConstructorFactory(slug="merc")
    finished_season(2019, ham, ver, team)
    finished_season(2020, ham, ver, team)
    finished_season(2021, ver, ham)
    # An ongoing season does not count: no results for its last round.
    ongoing = make_round(2022, 1, dt.date(2022, 6, 1))
    f.SessionFactory(round=ongoing, type=RACE)
    sf.DriverStandingFactory(season=ongoing.season, after_round=1, driver=nobody, position=1)

    rows = {d["slug"]: d for d in client.get("/api/v1/drivers/").json()["results"]}
    assert rows["ham"]["titles"] == 2
    assert rows["ver"]["titles"] == 1
    assert rows["nobody"]["titles"] == 0
    champs = client.get("/api/v1/drivers/", {"champion": "true"}).json()["results"]
    assert {d["slug"] for d in champs} == {"ham", "ver"}
    non = client.get("/api/v1/drivers/", {"champion": "false"}).json()["results"]
    assert {d["slug"] for d in non} == {"nobody"}
    ordered = client.get("/api/v1/drivers/", {"ordering": "-titles"}).json()["results"]
    assert [d["slug"] for d in ordered][:2] == ["ham", "ver"]
    detail = client.get("/api/v1/drivers/ham/").json()
    assert detail["stats"]["titles"] == 2
    by_year = {s["year"]: s["championship_position"] for s in detail["seasons"]}
    assert by_year == {2019: 1, 2020: 1, 2021: 2}
    ctors = client.get("/api/v1/constructors/").json()["results"]
    assert {c["slug"]: c["titles"] for c in ctors if c["slug"] == "merc"} == {"merc": 2}
    cdetail = client.get("/api/v1/constructors/merc/").json()
    assert cdetail["stats"]["titles"] == 2
    assert {s["year"]: s["championship_position"] for s in cdetail["seasons"]} == {
        2019: 1,
        2020: 1,
    }
    seasons = {s["year"]: s for s in client.get("/api/v1/seasons/").json()["results"]}
    assert seasons[2021]["driver_champion"]["slug"] == "ver"
    assert seasons[2019]["constructor_champion"]["slug"] == "merc"
    assert seasons[2022]["driver_champion"] is None
    assert seasons[2022]["constructor_champion"] is None


def test_driver_without_results_has_null_stats_but_list_titles_zero(client):
    f.DriverFactory(slug="rookie")
    assert client.get("/api/v1/drivers/rookie/").json()["stats"]["titles"] is None
    assert client.get("/api/v1/drivers/").json()["results"][0]["titles"] == 0


# --- Compare ---------------------------------------------------------------------------------


def seed_compare():
    a = f.DriverFactory(slug="aaa", given_name="Aaa", family_name="Alpha")
    b = f.DriverFactory(slug="bbb", given_name="Bbb", family_name="Beta")
    c = f.DriverFactory(slug="ccc")
    team, other = f.ConstructorFactory(slug="t1"), f.ConstructorFactory(slug="t2")
    # 1990 (grid based), 2000 (qualifying based), 2023 teammates.
    r90 = make_round(1990, 1, dt.date(1990, 3, 1))
    race_result(r90, a, team, position=1, position_text="1", grid=2)
    race_result(r90, b, other, position=2, position_text="2", grid=1)
    r90b = make_round(1990, 2, dt.date(1990, 3, 8))
    race_result(r90b, a, team, position=5, position_text="5", grid=3)
    race_result(r90b, b, other, position=20, position_text="R", grid=4)  # retired: not compared
    r00 = make_round(2000, 1, dt.date(2000, 3, 1))
    race_result(r00, a, team, position=3, position_text="3", grid=1)
    race_result(r00, b, other, position=4, position_text="4", grid=2)
    q = f.SessionFactory(round=r00, type=QUALI)
    f.QualifyingResultFactory(session=q, driver=a, constructor=team, position=4)
    f.QualifyingResultFactory(session=q, driver=b, constructor=other, position=2)
    r23 = make_round(2023, 1, dt.date(2023, 3, 5))
    race_result(r23, a, team, position=8, position_text="8", grid=8)
    race_result(r23, b, team, position=6, position_text="6", grid=7)
    race_result(r23, c, other, position=1, position_text="1", grid=1)
    q23 = f.SessionFactory(round=r23, type=QUALI)
    f.QualifyingResultFactory(session=q23, driver=a, constructor=team, position=9)
    f.QualifyingResultFactory(session=q23, driver=b, constructor=team, position=10)
    return a, b


def test_compare_head_to_head_and_stats(client):
    seed_compare()
    body = client.get("/api/v1/compare/", {"a": "aaa", "b": "bbb"}).json()
    assert body["a"]["driver"]["slug"] == "aaa"
    assert body["a"]["stats"]["starts"] == 4
    assert body["b"]["stats"]["wins"] == 0
    h2h = body["head_to_head"]
    assert h2h["races_together"] == 4
    assert h2h["same_team_races"] == 1
    # Both classified: 1990 R1 (a), 2000 (a), 2023 (b); 1990 R2 has a retirement.
    assert h2h["race"] == {"both_finished": 3, "a_ahead": 2, "b_ahead": 1}
    # Grid in 1990: R1 b ahead (1 vs 2), R2 a ahead (3 vs 4); 2000 quali: b (2 vs 4);
    # 2023 quali: a (9 vs 10). The grid of 2000 (a on pole) is ignored in favour of qualifying.
    assert h2h["qualifying"] == {"compared": 4, "a_ahead": 2, "b_ahead": 2}
    assert [s["year"] for s in h2h["teammate_seasons"]] == [2023]
    season = h2h["teammate_seasons"][0]
    assert season["team_slug"] == "t1"
    assert season["lap_times"] is None
    assert "not available" in season["lap_times_reason"]


def test_compare_season_filter_and_errors(client):
    seed_compare()
    body = client.get("/api/v1/compare/", {"a": "aaa", "b": "bbb", "season": 1990}).json()
    assert body["head_to_head"]["races_together"] == 2
    assert body["head_to_head"]["teammate_seasons"] == []
    assert client.get("/api/v1/compare/", {"a": "aaa"}).status_code == 400
    assert client.get("/api/v1/compare/", {"a": "aaa", "b": "aaa"}).status_code == 400
    assert client.get("/api/v1/compare/", {"a": "aaa", "b": "nope"}).status_code == 404


def test_compare_lap_time_hook_extension_point(client, monkeypatch):
    seed_compare()
    calls = []

    def provider(year, slug_a, slug_b):
        calls.append((year, slug_a, slug_b))
        return [
            {
                "round": 1,
                "name": "GP",
                "a_median_lap_ms": 90500,
                "b_median_lap_ms": 90000,
                "delta_ms": 500,
            }
        ]

    monkeypatch.setattr(compare_api, "LAP_TIME_PROVIDER", provider)
    season = client.get("/api/v1/compare/", {"a": "aaa", "b": "bbb"}).json()["head_to_head"][
        "teammate_seasons"
    ][0]
    assert calls == [(2023, "aaa", "bbb")]
    assert season["lap_times"][0]["delta_ms"] == 500
    assert season["lap_times_reason"] is None
    monkeypatch.setattr(compare_api, "LAP_TIME_PROVIDER", lambda *a: None)
    season = client.get("/api/v1/compare/", {"a": "aaa", "b": "bbb"}).json()["head_to_head"][
        "teammate_seasons"
    ][0]
    assert season["lap_times"] is None
    assert season["lap_times_reason"] == compare_api.REASON_NO_DATA


# --- Matrix ----------------------------------------------------------------------------------


def test_matrix_grid_categories_and_order(client):
    r1 = make_round(2024, 1, dt.date(2024, 3, 1), name="One")
    r2 = make_round(2024, 2, dt.date(2024, 3, 8), name="Two")
    r3 = make_round(2024, 3, dt.date(2024, 3, 15), name="Three")
    make_round(2024, None, dt.date(2024, 3, 22), is_cancelled=True)
    team = f.ConstructorFactory(slug="t1")
    f.ConstructorSeasonFactory(constructor=team, season=r1.season, color_hex="#abcdef")
    a, b, c = (f.DriverFactory(family_name=n) for n in ("Aa", "Bb", "Cc"))
    spec = {
        r1: [(a, 1, "1", 25), (b, 2, "2", 18), (c, 11, "11", 0)],
        r2: [(a, 2, "2", 18), (b, 6, "6", 8), (c, 20, "R", 0)],
        r3: [(a, 12, "12", 0), (c, 4, "4", 12)],
    }
    for rnd, rows in spec.items():
        for driver, position, text, points in rows:
            race_result(rnd, driver, team, position=position, position_text=text, points=points)
    sf.DriverStandingFactory(season=r1.season, after_round=3, driver=b, position=1)
    sf.DriverStandingFactory(season=r1.season, after_round=3, driver=a, position=2)
    body = client.get("/api/v1/seasons/2024/matrix/").json()
    assert [r["round"] for r in body["rounds"]] == [1, 2, 3]
    assert [d["slug"] for d in body["drivers"]] == [
        b.slug,
        a.slug,
        c.slug,
    ]  # standings, then points
    by = {d["slug"]: d for d in body["drivers"]}
    assert [c_["category"] for c_ in by[a.slug]["cells"]] == ["win", "podium", "no_points"]
    assert [c_["category"] for c_ in by[b.slug]["cells"][:2]] == ["podium", "points"]
    assert by[b.slug]["cells"][2] is None
    assert [c_["category"] for c_ in by[c.slug]["cells"]] == ["no_points", "dnf", "points"]
    assert by[c.slug]["cells"][1]["position"] is None
    assert by[a.slug]["team"]["color"] == "#abcdef"
    assert by[b.slug]["position"] == 1
    assert by[c.slug]["position"] is None
    assert by[a.slug]["points"] == 43
    assert client.get("/api/v1/seasons/1900/matrix/").status_code == 404
    empty = f.SeasonFactory(year=2001)
    assert client.get(f"/api/v1/seasons/{empty.year}/matrix/").json() == {
        "year": 2001,
        "rounds": [],
        "drivers": [],
    }


# --- Query counts (no N+1) -------------------------------------------------------------------


def seed_big_season(drivers=20, rounds=10):
    season = f.SeasonFactory(year=2024)
    team = f.ConstructorFactory()
    f.ConstructorSeasonFactory(constructor=team, season=season, color_hex="#123456")
    people = [f.DriverFactory() for _ in range(drivers)]
    for n in range(1, rounds + 1):
        rnd = f.RoundFactory(
            season=season, round=n, date=dt.date(2024, 1, 1) + dt.timedelta(days=n)
        )
        race = f.SessionFactory(round=rnd, type=RACE, start_utc=at(2024, 1, n, 14))
        f.SessionFactory(round=rnd, type=Session.Type.FP1, start_utc=at(2024, 1, n, 10))
        for position, driver in enumerate(people, start=1):
            f.ResultFactory(
                session=race, driver=driver, constructor=team, position=position, points=1
            )
    for position, driver in enumerate(people, start=1):
        sf.DriverStandingFactory(
            season=season, after_round=rounds, driver=driver, position=position
        )
    return people


def test_new_endpoints_have_bounded_query_counts(client, django_assert_max_num_queries):
    people = seed_big_season()
    urls = [
        ("/api/v1/calendar/", 6),
        ("/api/v1/calendar/ics/?year=2024", 6),
        ("/api/v1/dashboard/", 22),
        ("/api/v1/seasons/2024/matrix/", 8),
        (f"/api/v1/compare/?a={people[0].slug}&b={people[1].slug}", 22),
        ("/api/v1/drivers/?champion=true", 8),
    ]
    for url, limit in urls:
        with django_assert_max_num_queries(limit):
            response = client.get(url)
        assert response.status_code == 200, url

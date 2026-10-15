import datetime as dt

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Session

from . import factories as f

pytestmark = pytest.mark.django_db

RACE = Session.Type.RACE
SPRINT = Session.Type.SPRINT
QUALI = Session.Type.Q


@pytest.fixture
def client():
    return APIClient()


def get(client, url, **params):
    return client.get(url, params)


def make_round(year=2024, number=1, date=dt.date(2024, 3, 2), **kwargs):
    season = f.SeasonFactory._meta.model.objects.filter(year=year).first() or f.SeasonFactory(
        year=year
    )
    return f.RoundFactory(season=season, round=number, date=date, **kwargs)


def race_result(rnd, driver, constructor, session_type=RACE, **kwargs):
    session = Session.objects.filter(round=rnd, type=session_type).first() or f.SessionFactory(
        round=rnd, type=session_type
    )
    return f.ResultFactory(session=session, driver=driver, constructor=constructor, **kwargs)


# --- Access ----------------------------------------------------------------------------------


def test_read_only_and_anonymous(client):
    assert get(client, "/api/v1/drivers/").status_code == 200
    assert client.post("/api/v1/drivers/", {}).status_code == 405
    assert client.delete("/api/v1/drivers/x/").status_code == 405


# --- Drivers ---------------------------------------------------------------------------------


def test_driver_list_pagination(client):
    for _ in range(30):
        f.DriverFactory()
    body = get(client, "/api/v1/drivers/").json()
    assert body["count"] == 30
    assert len(body["results"]) == 25
    assert len(get(client, "/api/v1/drivers/", page=2).json()["results"]) == 5
    assert len(get(client, "/api/v1/drivers/", page_size=10).json()["results"]) == 10
    assert len(get(client, "/api/v1/drivers/", page_size=1000).json()["results"]) == 30
    assert get(client, "/api/v1/drivers/", page=9).status_code == 404


def test_driver_list_filters(client):
    ham = f.DriverFactory(given_name="Lewis", family_name="Hamilton", nationality="British")
    ver = f.DriverFactory(given_name="Max", family_name="Verstappen", nationality="Dutch")
    old = f.DriverFactory(given_name="Old", family_name="Timer", nationality="British")
    red, mer = f.ConstructorFactory(slug="red-bull"), f.ConstructorFactory(slug="mercedes")
    r24, r88 = make_round(2024, 1), make_round(1988, 1)
    race_result(r24, ham, mer, position=1)
    race_result(r24, ver, red, position=2)
    race_result(r88, old, mer, position=1)

    def slugs(**params):
        return {d["slug"] for d in get(client, "/api/v1/drivers/", **params).json()["results"]}

    assert slugs(season=1988) == {old.slug}
    assert slugs(nationality="british") == {ham.slug, old.slug}
    assert slugs(constructor="red-bull") == {ver.slug}
    assert slugs(active="true") == {ham.slug, ver.slug}
    assert slugs(active="false") == {old.slug}
    assert slugs(q="hamil") == {ham.slug}


def test_driver_list_champion_filter_without_standings_finds_nobody(client):
    driver = f.DriverFactory()
    assert get(client, "/api/v1/drivers/", champion="true").json()["results"] == []
    everyone = get(client, "/api/v1/drivers/", champion="false").json()["results"]
    assert [r["slug"] for r in everyone] == [driver.slug]


def test_driver_search_ignores_diacritics_and_case(client):
    kimi = f.DriverFactory(given_name="Kimi", family_name="Räikkönen")
    f.DriverFactory(given_name="Max", family_name="Verstappen")
    results = get(client, "/api/v1/drivers/", q="RAIKKONEN").json()["results"]
    assert [d["slug"] for d in results] == [kimi.slug]


def test_driver_list_ordering_and_validation(client):
    a = f.DriverFactory(family_name="Aaa")
    b = f.DriverFactory(family_name="Bbb")
    c = f.ConstructorFactory()
    rnd = make_round()
    race_result(rnd, b, c, position=1)
    race_result(rnd, a, c, position=2)
    results = get(client, "/api/v1/drivers/", ordering="-wins").json()["results"]
    assert [d["slug"] for d in results] == [b.slug, a.slug]
    assert [d["wins"] for d in results] == [1, 0]
    assert get(client, "/api/v1/drivers/", ordering="-starts").status_code == 200
    assert get(client, "/api/v1/drivers/", ordering="titles").status_code == 200
    assert get(client, "/api/v1/drivers/", ordering="bogus").status_code == 400
    assert get(client, "/api/v1/drivers/", season="abc").status_code == 400
    assert get(client, "/api/v1/drivers/", season=1900).status_code == 400


def test_driver_list_row_nulls(client):
    f.DriverFactory(family_name="Nobody")
    row = get(client, "/api/v1/drivers/").json()["results"][0]
    assert row["team"] is None
    assert row["titles"] == 0  # no standings imported means no titles, never null
    assert row["code"] is None
    assert row["number"] is None
    assert row["nationality"] is None
    assert row["starts"] == 0


def test_driver_list_team_is_latest_race_day_team(client):
    driver = f.DriverFactory()
    old_team = f.ConstructorFactory(name="Old Team")
    new_team = f.ConstructorFactory(name="New Team", slug="new-team")
    r1 = make_round(2024, 1, dt.date(2024, 3, 2))
    r2 = make_round(2024, 2, dt.date(2024, 3, 9))
    race_result(r1, driver, old_team, position=1)
    race_result(r2, driver, new_team, position=1)
    f.ConstructorSeasonFactory(constructor=new_team, season=r2.season, color_hex="#112233")
    row = get(client, "/api/v1/drivers/").json()["results"][0]
    assert row["team"] == {"slug": "new-team", "name": "New Team", "color": "#112233"}


def test_driver_detail_stats_seasons_and_last_results(client):
    driver = f.DriverFactory(given_name="Sergio", family_name="Perez")
    team_a, team_b = f.ConstructorFactory(name="Alpha"), f.ConstructorFactory(name="Beta")
    # Pre-1994 pole comes from the grid, later poles from qualifying.
    old = make_round(1990, 1, dt.date(1990, 3, 1))
    race_result(old, driver, team_a, position=1, grid=1, points=9, fastest_lap_rank=1)
    new = make_round(2024, 1, dt.date(2024, 3, 2))
    race_result(new, driver, team_a, position=3, grid=5, points=15)
    sprint = f.SessionFactory(round=new, type=SPRINT)
    f.ResultFactory(session=sprint, driver=driver, constructor=team_a, position=2, points=7)
    q = f.SessionFactory(round=new, type=QUALI)
    f.QualifyingResultFactory(session=q, driver=driver, constructor=team_a, position=1)
    # Grid 1 after 1994 does not count as a pole; only qualifying does.
    later = make_round(2024, 2, dt.date(2024, 3, 9))
    race_result(later, driver, team_b, position=None, grid=1, points=0)

    body = get(client, f"/api/v1/drivers/{driver.slug}/").json()
    assert body["stats"] == {
        "starts": 3,
        "wins": 1,
        "podiums": 2,
        "poles": 2,
        "fastest_laps": 1,
        "points": 31.0,
        "titles": 0,
    }
    seasons = {s["year"]: s for s in body["seasons"]}
    assert [s["year"] for s in body["seasons"]] == [2024, 1990]
    assert [t["name"] for t in seasons[2024]["teams"]] == ["Alpha", "Beta"]
    assert seasons[2024]["points"] == 22.0
    assert seasons[2024]["championship_position"] is None
    assert seasons[1990]["wins"] == 1
    assert body["last_results"][0]["round"] == 2
    assert body["last_results"][0]["position"] is None
    assert body["team"]["name"] == "Beta"


def test_driver_detail_without_results_is_all_null(client):
    driver = f.DriverFactory()
    body = get(client, f"/api/v1/drivers/{driver.slug}/").json()
    assert all(v is None for v in body["stats"].values())
    assert body["seasons"] == []
    assert body["last_results"] == []
    assert body["team"] is None
    assert body["date_of_birth"] is None


def test_driver_last_results_capped_at_ten(client):
    driver, team = f.DriverFactory(), f.ConstructorFactory()
    for n in range(1, 13):
        race_result(make_round(2024, n, dt.date(2024, 1, 1) + dt.timedelta(days=n)), driver, team)
    body = get(client, f"/api/v1/drivers/{driver.slug}/").json()
    assert len(body["last_results"]) == 10
    assert body["last_results"][0]["round"] == 12


def test_driver_detail_404(client):
    assert get(client, "/api/v1/drivers/nobody/").status_code == 404


def test_constructor_on_race_day_preserved_after_transfer(client):
    driver = f.DriverFactory()
    old_team = f.ConstructorFactory(slug="old-team", name="Old Team")
    new_team = f.ConstructorFactory(slug="new-team", name="New Team")
    r1 = make_round(2023, 1, dt.date(2023, 3, 5))
    race_result(r1, driver, old_team, position=1)
    r2 = make_round(2024, 1, dt.date(2024, 3, 2))
    race_result(r2, driver, new_team, position=1)

    results = get(client, "/api/v1/rounds/2023/1/results/").json()["results"]
    assert results[0]["team"]["slug"] == "old-team"
    circuit = get(client, f"/api/v1/circuits/{r1.circuit.slug}/").json()
    assert circuit["winners"][0]["team"]["slug"] == "old-team"
    season = get(client, "/api/v1/seasons/2023/").json()
    assert season["rounds"][0]["winner"]["team"]["slug"] == "old-team"
    old = get(client, "/api/v1/constructors/old-team/").json()
    assert [d["slug"] for d in old["current_drivers"]] == [driver.slug]
    assert old["current_season"] == 2023
    detail = get(client, f"/api/v1/drivers/{driver.slug}/").json()
    assert [s["teams"][0]["slug"] for s in detail["seasons"]] == ["new-team", "old-team"]


# --- Constructors ----------------------------------------------------------------------------


def test_constructor_list_filters_ordering(client):
    a = f.ConstructorFactory(name="Alpha", nationality="Italian")
    b = f.ConstructorFactory(name="Beta", nationality="British")
    f.ConstructorFactory(name="Idle")
    d1, d2 = f.DriverFactory(), f.DriverFactory()
    rnd = make_round(2024, 1)
    race_result(rnd, d1, b, position=1)
    race_result(rnd, d2, b, position=2)
    other = make_round(2000, 1)
    race_result(other, d1, a, position=1)

    rows = get(client, "/api/v1/constructors/", ordering="-wins").json()["results"]
    assert rows[0]["slug"] in {a.slug, b.slug}
    by_slug = {r["slug"]: r for r in rows}
    assert by_slug[b.slug]["starts"] == 1  # two cars, one race
    assert by_slug[b.slug]["titles"] == 0
    assert by_slug[a.slug]["wins"] == 1
    assert {
        r["slug"] for r in get(client, "/api/v1/constructors/", season=2000).json()["results"]
    } == {a.slug}
    assert {
        r["slug"]
        for r in get(client, "/api/v1/constructors/", nationality="british").json()["results"]
    } == {b.slug}
    assert get(client, "/api/v1/constructors/", ordering="x").status_code == 400


def test_constructor_detail(client):
    team = f.ConstructorFactory(slug="ferrari", nationality="")
    d1, d2 = f.DriverFactory(family_name="Aaa"), f.DriverFactory(family_name="Bbb")
    r1 = make_round(1990, 1, dt.date(1990, 3, 5))
    race_result(r1, d1, team, position=1, points=25, grid=1)
    race_result(r1, d2, team, position=2, points=18, grid=2)
    r2 = make_round(2024, 1, dt.date(2024, 3, 2))
    race_result(r2, d1, team, position=5, points=10)
    f.ConstructorSeasonFactory(constructor=team, season=r2.season, color_hex="#ff0000")

    body = get(client, "/api/v1/constructors/ferrari/").json()
    assert body["nationality"] is None
    assert body["stats"]["starts"] == 2
    assert body["stats"]["wins"] == 1
    assert body["stats"]["podiums"] == 2
    assert body["stats"]["points"] == 53.0
    assert body["stats"]["poles"] == 1
    assert body["stats"]["titles"] == 0
    assert [s["year"] for s in body["seasons"]] == [2024, 1990]
    assert body["seasons"][0]["color"] == "#ff0000"
    assert body["seasons"][1]["color"] is None
    assert len(body["seasons"][1]["drivers"]) == 2
    assert body["current_season"] == 2024
    assert [d["slug"] for d in body["current_drivers"]] == [d1.slug]
    assert get(client, "/api/v1/constructors/nope/").status_code == 404


# --- Circuits --------------------------------------------------------------------------------


def test_circuit_list_and_detail(client):
    circuit = f.CircuitFactory(slug="monza", name="Monza", country="Italy", lat=45.62, lng=9.28)
    unused = f.CircuitFactory(slug="new", name="Newtrack", country="Spain")
    driver, team = f.DriverFactory(), f.ConstructorFactory()
    r1 = f.RoundFactory(
        season=f.SeasonFactory(year=2023), round=1, circuit=circuit, date=dt.date(2023, 9, 3)
    )
    r2 = f.RoundFactory(
        season=f.SeasonFactory(year=2024), round=1, circuit=circuit, date=dt.date(2024, 9, 1)
    )
    f.RoundFactory(
        season=r2.season, round=2, circuit=circuit, date=dt.date(2024, 10, 1), is_cancelled=True
    )
    f.RoundFactory(
        season=r2.season, round=3, circuit=circuit, date=dt.date(2999, 1, 1)
    )  # in the future
    race_result(r1, driver, team, position=1)
    race_result(r2, driver, team, position=1)

    rows = {r["slug"]: r for r in get(client, "/api/v1/circuits/").json()["results"]}
    assert rows["monza"]["gp_count"] == 2
    assert rows["monza"]["last_gp_date"] == "2024-09-01"
    assert rows["monza"]["country"] == "Italy"
    assert rows[unused.slug]["gp_count"] == 0
    assert rows[unused.slug]["last_gp_date"] is None
    assert rows[unused.slug]["locality"] is None
    assert [
        r["slug"] for r in get(client, "/api/v1/circuits/", country="spain").json()["results"]
    ] == ["new"]
    assert [r["slug"] for r in get(client, "/api/v1/circuits/", q="mon").json()["results"]] == [
        "monza"
    ]
    ordered = get(client, "/api/v1/circuits/", ordering="-gp_count").json()["results"]
    assert ordered[0]["slug"] == "monza"

    body = get(client, "/api/v1/circuits/monza/").json()
    assert body["gp_count"] == 2
    assert [w["year"] for w in body["winners"]] == [2024, 2023]
    assert body["most_wins_drivers"][0]["wins"] == 2
    assert body["most_wins_teams"][0]["slug"] == team.slug
    assert body["lat"] == pytest.approx(45.62)
    assert body["length_m"] is None
    assert body["lap_record_driver"] is None
    empty = get(client, "/api/v1/circuits/new/").json()
    assert empty["winners"] == [] and empty["lat"] is None
    assert get(client, "/api/v1/circuits/nope/").status_code == 404


# --- Seasons and rounds ----------------------------------------------------------------------


def test_season_list(client):
    s24 = f.SeasonFactory(year=2024)
    f.SeasonFactory(year=2023)
    r1 = f.RoundFactory(season=s24, round=1)
    f.RoundFactory(season=s24, round=2)
    f.RoundFactory(season=s24, round=None, is_cancelled=True)
    f.SessionFactory(round=r1, type=SPRINT)
    f.SessionFactory(round=r1, type=RACE)
    rows = get(client, "/api/v1/seasons/").json()["results"]
    assert [r["year"] for r in rows] == [2024, 2023]
    assert rows[0]["rounds_count"] == 3
    assert rows[0]["cancelled_rounds"] == 1
    assert rows[0]["sprint_rounds"] == 1
    assert rows[0]["driver_champion"] is None
    assert rows[1]["rounds_count"] == 0
    assert rows[0]["name"] is None


def test_season_detail_calendar(client):
    season = f.SeasonFactory(year=2024)
    done = f.RoundFactory(season=season, round=1, date=dt.date(2024, 3, 2))
    f.RoundFactory(season=season, round=2, date=dt.date(2024, 3, 9))
    f.RoundFactory(season=season, round=None, date=dt.date(2024, 3, 16), is_cancelled=True)
    f.SessionFactory(round=done, type=SPRINT)
    winner, team = f.DriverFactory(), f.ConstructorFactory()
    race_result(done, winner, team, position=1)
    race_result(done, f.DriverFactory(), team, position=2)
    body = get(client, "/api/v1/seasons/2024/").json()
    assert body["sprint_rounds"] == 1
    rounds = body["rounds"]
    assert [r["round"] for r in rounds] == [1, 2, None]
    assert rounds[0]["winner"]["driver"]["slug"] == winner.slug
    assert rounds[0]["has_sprint"] is True
    assert rounds[1]["winner"] is None
    assert rounds[2]["is_cancelled"] is True
    assert get(client, "/api/v1/seasons/1999/").status_code == 404


def test_round_detail(client):
    season = f.SeasonFactory(year=2024)
    f.RoundFactory(season=season, round=1, name="Opening GP")
    middle = f.RoundFactory(season=season, round=2, name="Middle GP")
    f.RoundFactory(season=season, round=3, name="Closing GP")
    f.SessionFactory(round=middle, type=RACE)
    f.SessionFactory(round=middle, type=QUALI)
    f.ResultFactory(session=middle.sessions.get(type=RACE))
    body = get(client, "/api/v1/rounds/2024/2/").json()
    assert body["name"] == "Middle GP"
    assert {s["type"]: s["has_results"] for s in body["sessions"]} == {"RACE": True, "Q": False}
    assert body["previous_round"]["round"] == 1
    assert body["next_round"]["name"] == "Closing GP"
    assert body["scheduled_laps"] is None
    assert body["circuit"]["length_m"] is None
    first = get(client, "/api/v1/rounds/2024/1/").json()
    assert first["previous_round"] is None
    assert get(client, "/api/v1/rounds/2024/9/").status_code == 404
    assert get(client, "/api/v1/rounds/1999/1/").status_code == 404


def test_race_results(client):
    rnd = make_round()
    team = f.ConstructorFactory(slug="team")
    f.ConstructorSeasonFactory(constructor=team, season=rnd.season, color_hex="#abcdef")
    d1, d2, d3, d4 = (f.DriverFactory() for _ in range(4))
    race_result(
        rnd,
        d1,
        team,
        position=1,
        position_text="1",
        grid=3,
        laps=57,
        status="Finished",
        time_ms=5_400_000,
        points=25,
        fastest_lap_rank=1,
    )
    race_result(rnd, d2, team, position=2, grid=1, status="Finished", points=18)
    race_result(rnd, d3, team, position=3, grid=0)
    race_result(rnd, d4, team, position=None, position_text="R", grid=4, status="Engine", points=0)
    body = get(client, "/api/v1/rounds/2024/1/results/").json()
    assert body["session"]["type"] == "RACE"
    rows = body["results"]
    assert rows[0]["position_change"] == 2
    assert rows[0]["fastest_lap"] is True
    assert rows[0]["team"] == {"slug": "team", "name": team.name, "color": "#abcdef"}
    assert rows[0]["time_ms"] == 5_400_000
    assert rows[1]["position_change"] == -1
    assert rows[1]["fastest_lap"] is None
    assert rows[1]["time_ms"] is None and rows[1]["laps"] is None
    assert rows[2]["position_change"] is None  # pit lane start
    assert rows[2]["status"] is None
    assert rows[3]["position"] is None and rows[3]["position_text"] == "R"
    assert rows[3]["position_change"] is None


def test_sprint_and_qualifying_results(client):
    rnd = make_round()
    team = f.ConstructorFactory()
    race_result(rnd, f.DriverFactory(), team, session_type=SPRINT, position=1, points=8)
    q = f.SessionFactory(round=rnd, type=QUALI)
    names = {}
    for position, times in enumerate(
        [(80_000, 79_000, 78_000), (80_100, 79_100, None), (80_200, None, None)], start=1
    ):
        driver = f.DriverFactory()
        names[position] = driver.slug
        f.QualifyingResultFactory(
            session=q,
            driver=driver,
            constructor=team,
            position=position,
            q1_ms=times[0],
            q2_ms=times[1],
            q3_ms=times[2],
        )
    sprint = get(client, "/api/v1/rounds/2024/1/results/", session="SPRINT").json()
    assert sprint["results"][0]["points"] == 8.0
    rows = get(client, "/api/v1/rounds/2024/1/results/", session="Q").json()["results"]
    assert [r["eliminated_in"] for r in rows] == [None, "Q2", "Q1"]
    assert rows[2]["q2_ms"] is None and rows[2]["q3_ms"] is None
    assert rows[0]["driver"]["slug"] == names[1]


def test_results_errors(client):
    rnd = make_round()
    f.SessionFactory(round=rnd, type=RACE)
    assert get(client, "/api/v1/rounds/2024/1/results/", session="FP1").status_code == 400
    assert get(client, "/api/v1/rounds/2024/1/results/", session="SPRINT").status_code == 404
    assert get(client, "/api/v1/rounds/2024/7/results/").status_code == 404
    assert get(client, "/api/v1/rounds/2024/1/results/").json()["results"] == []


# --- Search ----------------------------------------------------------------------------------


def test_search_groups_and_diacritics(client):
    kimi = f.DriverFactory(given_name="Kimi", family_name="Räikkönen")
    f.ConstructorFactory(slug="sauber", name="Sauber")
    f.CircuitFactory(slug="interlagos", name="Autódromo José Carlos Pace", country="Brazil")
    season = f.SeasonFactory(year=2024)
    f.RoundFactory(season=season, round=1, name="São Paulo Grand Prix")
    f.RoundFactory(season=season, round=None, name="São Paulo cancelled")

    assert [d["slug"] for d in get(client, "/api/v1/search/", q="raikkonen").json()["drivers"]] == [
        kimi.slug
    ]
    assert get(client, "/api/v1/search/", q="SAUB").json()["constructors"][0]["slug"] == "sauber"
    assert (
        get(client, "/api/v1/search/", q="jose carlos").json()["circuits"][0]["slug"]
        == "interlagos"
    )
    rounds = get(client, "/api/v1/search/", q="sao paulo").json()["rounds"]
    assert [(r["year"], r["round"]) for r in rounds] == [(2024, 1)]


def test_search_validation_and_limit(client):
    assert get(client, "/api/v1/search/").status_code == 400
    assert get(client, "/api/v1/search/", q="a").status_code == 400
    for n in range(8):
        f.DriverFactory(given_name="Match", family_name=f"Zed{n}")
        f.ConstructorFactory(name=f"Zed team {n}")
        f.CircuitFactory(name=f"Zed circuit {n}")
        f.RoundFactory(name=f"Zed GP {n}", season=f.SeasonFactory(year=1950 + n), round=1)
    body = get(client, "/api/v1/search/", q="zed").json()
    assert {k: len(v) for k, v in body.items()} == {
        "drivers": 5,
        "constructors": 5,
        "circuits": 5,
        "rounds": 5,
    }
    empty = get(client, "/api/v1/search/", q="qqqq").json()
    assert all(v == [] for v in empty.values())


# --- Query counts (no N+1) -------------------------------------------------------------------


def seed_30_rows():
    """30 drivers, constructors, circuits and rounds with results in one season."""
    season = f.SeasonFactory(year=2024)
    for n in range(30):
        circuit = f.CircuitFactory()
        rnd = f.RoundFactory(
            season=season,
            round=n + 1,
            circuit=circuit,
            date=dt.date(2024, 1, 1) + dt.timedelta(days=n),
        )
        team = f.ConstructorFactory()
        f.ConstructorSeasonFactory(constructor=team, season=season, color_hex="#123456")
        driver = f.DriverFactory()
        race = f.SessionFactory(round=rnd, type=RACE)
        f.ResultFactory(session=race, driver=driver, constructor=team, position=1)
        q = f.SessionFactory(round=rnd, type=QUALI)
        f.QualifyingResultFactory(session=q, driver=driver, constructor=team, position=1)
    return season


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/drivers/",
        "/api/v1/constructors/",
        "/api/v1/circuits/",
        "/api/v1/seasons/",
        "/api/v1/seasons/2024/",
        "/api/v1/rounds/2024/1/",
        "/api/v1/search/?q=Given",
        "/api/v1/search/?q=Circuit",
    ],
)
def test_list_endpoints_have_constant_query_count(client, django_assert_max_num_queries, url):
    seed_30_rows()
    with django_assert_max_num_queries(8):
        response = client.get(url)
    assert response.status_code == 200


def test_results_endpoint_constant_query_count(client, django_assert_max_num_queries):
    rnd = make_round()
    for position in range(1, 31):
        race_result(rnd, f.DriverFactory(), f.ConstructorFactory(), position=position)
    q = f.SessionFactory(round=rnd, type=QUALI)
    for position in range(1, 31):
        f.QualifyingResultFactory(session=q, position=position)
    for session in ("RACE", "Q"):
        with django_assert_max_num_queries(6):
            assert (
                client.get("/api/v1/rounds/2024/1/results/", {"session": session}).status_code
                == 200
            )


def test_detail_endpoints_constant_query_count(client, django_assert_max_num_queries):
    seed_30_rows()
    from apps.catalog.models import Circuit, Constructor, Driver

    driver, team, circuit = (
        Driver.objects.first(),
        Constructor.objects.first(),
        Circuit.objects.first(),
    )
    for url in (
        f"/api/v1/drivers/{driver.slug}/",
        f"/api/v1/constructors/{team.slug}/",
        f"/api/v1/circuits/{circuit.slug}/",
    ):
        with django_assert_max_num_queries(10):
            assert client.get(url).status_code == 200


def test_driver_list_exposes_ids_so_a_season_grid_can_be_picked(client):
    rnd = make_round(2024, 1)
    ver = f.DriverFactory(family_name="Verstappen")
    race_result(rnd, ver, f.ConstructorFactory(), position=1)

    rows = get(client, "/api/v1/drivers/", season=2024, page_size=100).json()["results"]

    assert [(r["id"], r["slug"]) for r in rows] == [(ver.id, ver.slug)]

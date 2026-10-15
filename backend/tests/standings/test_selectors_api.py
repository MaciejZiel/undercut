from decimal import Decimal

import pytest

from apps.standings import selectors
from apps.standings.models import ConstructorStanding, DriverStanding

from .factories import (
    ConstructorFactory,
    ConstructorStandingFactory,
    DriverFactory,
    DriverStandingFactory,
    SeasonFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def season_data():
    """Three drivers over three rounds; B scores half points in round 2, C skips round 3."""
    season = SeasonFactory(year=2024)
    a = DriverFactory(given_name="Ann", family_name="Alpha", code="ALP")
    b = DriverFactory(given_name="Bob", family_name="Beta", code="BET")
    c = DriverFactory(given_name="Cy", family_name="Gamma", code="GAM")
    table = {
        1: [(a, 1, "25"), (b, 2, "18"), (c, 3, "15")],
        2: [(a, 1, "50"), (b, 2, "30.5"), (c, 3, "27")],
        3: [(b, 1, "60.5"), (a, 2, "50")],
    }
    for rnd, rows in table.items():
        for driver, pos, pts in rows:
            DriverStandingFactory(
                season=season,
                after_round=rnd,
                driver=driver,
                position=pos,
                position_text=str(pos),
                points=Decimal(pts),
            )
    return season, a, b, c


def test_latest_position_and_round(season_data):
    season, *_ = season_data
    SeasonFactory(year=2023)
    latest = selectors.latest_position("drivers")
    assert (latest.year, latest.after_round) == (2024, 3)
    assert selectors.latest_round("drivers", season.pk) == 3
    assert selectors.latest_position("constructors") is None
    assert selectors.available_rounds("drivers", season.pk) == [1, 2, 3]


def test_standings_gap_to_leader_default_latest(season_data):
    season, a, b, _ = season_data
    rows = selectors.standings_rows("drivers", season.pk)
    assert [r["entity"]["id"] for r in rows] == [b.pk, a.pk]
    assert rows[0]["gap_to_leader"] == 0
    assert rows[1]["gap_to_leader"] == Decimal("10.5")


def test_standings_after_round_half_points(season_data):
    season, *_ = season_data
    rows = selectors.standings_rows("drivers", season.pk, 2)
    assert [r["points"] for r in rows] == [Decimal("50"), Decimal("30.5"), Decimal("27")]
    assert rows[1]["gap_to_leader"] == Decimal("19.5")


def test_progression_alignment_and_half_points(season_data):
    season, a, b, c = season_data
    data = selectors.points_progression("drivers", season.pk, top=3)
    assert data["rounds"] == [1, 2, 3]
    by_id = {s["entity"]["id"]: s for s in data["series"]}
    assert by_id[b.pk]["points"] == [Decimal("18"), Decimal("30.5"), Decimal("60.5")]
    assert by_id[b.pk]["positions"] == [2, 2, 1]
    assert by_id[c.pk]["points"] == [Decimal("15"), Decimal("27"), None]
    assert by_id[c.pk]["positions"] == [3, 3, None]
    # final order: present in last round first (B, A), then the one that dropped out
    assert [s["entity"]["id"] for s in data["series"]] == [b.pk, a.pk, c.pk]


def test_progression_top_limits(season_data):
    season, _, b, _ = season_data
    data = selectors.points_progression("drivers", season.pk, top=1)
    assert [s["entity"]["id"] for s in data["series"]] == [b.pk]


def test_progression_empty_season():
    season = SeasonFactory()
    assert selectors.points_progression("drivers", season.pk) == {"rounds": [], "series": []}


# API


def test_drivers_default_latest_shape(client, season_data):
    SeasonFactory(year=2020)
    res = client.get("/api/v1/standings/drivers/")
    assert res.status_code == 200
    body = res.json()
    assert body["season"] == 2024
    assert body["after_round"] == 3
    assert body["rounds"] == [1, 2, 3]
    first = body["results"][0]
    assert set(first) == {
        "position",
        "position_text",
        "entity",
        "points",
        "wins",
        "podiums",
        "gap_to_leader",
    }
    assert set(first["entity"]) == {"id", "slug", "name", "code", "nationality"}
    assert first["entity"]["name"] == "Bob Beta"
    assert first["entity"]["code"] == "BET"
    assert first["points"] == 60.5
    assert body["results"][1]["gap_to_leader"] == 10.5


def test_drivers_after_round(client, season_data):
    body = client.get("/api/v1/standings/drivers/?season=2024&after_round=1").json()
    assert body["after_round"] == 1
    assert [r["points"] for r in body["results"]] == [25, 18, 15]


def test_drivers_no_n_plus_one(client, season_data, django_assert_num_queries):
    # season lookup, rounds list, rows (entity joined)
    with django_assert_num_queries(3):
        assert client.get("/api/v1/standings/drivers/?season=2024&after_round=2").status_code == 200
    # latest lookup, rounds list, rows
    with django_assert_num_queries(3):
        assert client.get("/api/v1/standings/drivers/").status_code == 200


def test_progress_api_shape_and_queries(client, season_data, django_assert_num_queries):
    with django_assert_num_queries(2):
        res = client.get("/api/v1/standings/drivers/progress/?season=2024&top=2")
    body = res.json()
    assert body["season"] == 2024
    assert body["rounds"] == [1, 2, 3]
    assert len(body["series"]) == 2
    assert body["series"][0]["points"] == [18, 30.5, 60.5]
    assert body["series"][0]["positions"] == [2, 2, 1]


def test_progress_default_top_is_five(client):
    season = SeasonFactory(year=2022)
    for _ in range(7):
        DriverStandingFactory(season=season, driver=DriverFactory())
    body = client.get("/api/v1/standings/drivers/progress/").json()
    assert len(body["series"]) == 5


def test_constructors_endpoints(client, django_assert_num_queries):
    season = SeasonFactory(year=2021)
    t1, t2 = ConstructorFactory(name="Red"), ConstructorFactory(name="Blue")
    for rnd, (p1, p2) in {1: ("10", "8"), 2: ("12.5", "20")}.items():
        ConstructorStandingFactory(
            season=season,
            after_round=rnd,
            constructor=t1,
            position=2 if rnd == 2 else 1,
            points=Decimal(p1),
        )
        ConstructorStandingFactory(
            season=season,
            after_round=rnd,
            constructor=t2,
            position=1 if rnd == 2 else 2,
            points=Decimal(p2),
        )
    with django_assert_num_queries(3):
        body = client.get("/api/v1/standings/constructors/?season=2021").json()
    assert body["results"][0]["entity"]["name"] == "Blue"
    assert body["results"][0]["entity"]["code"] is None
    assert body["results"][1]["gap_to_leader"] == 7.5
    prog = client.get("/api/v1/standings/constructors/progress/?season=2021").json()
    assert prog["series"][0]["entity"]["name"] == "Blue"
    assert prog["series"][1]["points"] == [10, 12.5]
    assert ConstructorStanding.objects.count() == 4


def test_empty_database_returns_empty_payload(client):
    body = client.get("/api/v1/standings/drivers/").json()
    assert body == {"season": None, "after_round": None, "rounds": [], "results": []}
    body = client.get("/api/v1/standings/constructors/progress/").json()
    assert body == {"season": None, "rounds": [], "series": []}


def test_unknown_season_is_404(client):
    for url in (
        "/api/v1/standings/drivers/?season=1999",
        "/api/v1/standings/constructors/?season=1999",
        "/api/v1/standings/drivers/progress/?season=1999",
        "/api/v1/standings/constructors/progress/?season=1999",
    ):
        res = client.get(url)
        assert res.status_code == 404
        assert "1999" in res.json()["detail"]


def test_missing_round_is_404(client, season_data):
    res = client.get("/api/v1/standings/drivers/?season=2024&after_round=9")
    assert res.status_code == 404
    assert "round 9" in res.json()["detail"]


def test_season_without_data_is_empty_ok(client):
    SeasonFactory(year=2010)
    body = client.get("/api/v1/standings/drivers/?season=2010").json()
    assert body["season"] == 2010
    assert body["results"] == []


@pytest.mark.parametrize("query", ["season=abc", "season=1800", "after_round=0", "after_round=x"])
def test_bad_table_params_are_400(client, season_data, query):
    assert client.get(f"/api/v1/standings/drivers/?{query}").status_code == 400
    assert client.get(f"/api/v1/standings/constructors/?{query}").status_code == 400


@pytest.mark.parametrize("query", ["season=abc", "season=1800", "top=0", "top=99", "top=many"])
def test_bad_progress_params_are_400(client, season_data, query):
    assert client.get(f"/api/v1/standings/drivers/progress/?{query}").status_code == 400
    assert client.get(f"/api/v1/standings/constructors/progress/?{query}").status_code == 400


def test_anonymous_read_only(client, season_data):
    assert client.post("/api/v1/standings/drivers/", {}).status_code == 405
    assert DriverStanding.objects.count() == 8

import datetime as dt
import sys
import types

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog import selectors as catalog
from apps.predictions import errors, exports, selectors, services
from apps.predictions.models import Prediction

from .conftest import NOW
from .factories import make_drivers, make_user, make_weekend, set_race_result

pytestmark = pytest.mark.django_db


def direct(user, round_, d, points, *, exact=0, pole_hit=False, podium=False):
    """Create a scored prediction directly (the scoring itself is tested elsewhere)."""
    return Prediction.objects.create(
        user=user,
        round=round_,
        p1=d[0],
        p2=d[1],
        p3=d[2],
        pole=d[3],
        fastest_lap=d[4],
        points=points,
        breakdown={"exact_hits": exact, "pole_hit": pole_hit, "exact_podium": podium},
    )


def names(board):
    return [row["name"] for row in board["results"]]


# --- Leaderboard ordering ------------------------------------------------------------------------


def test_orders_by_points_then_exact_hits_then_poles_then_registration(drivers, clock):
    round_, _, _ = make_weekend(2025, 1, quali_start=NOW)
    old = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    new = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
    top = make_user("top")
    more_exact = make_user("more_exact")
    more_poles = make_user("more_poles")
    early = make_user("early", joined=old)
    late = make_user("late", joined=new)
    direct(late, round_, drivers, 10, exact=1, pole_hit=False)
    direct(early, round_, drivers, 10, exact=1, pole_hit=False)
    direct(more_poles, round_, drivers, 10, exact=1, pole_hit=True)
    direct(more_exact, round_, drivers, 10, exact=2, pole_hit=False)
    direct(top, round_, drivers, 11, exact=0)
    board = selectors.leaderboard(season=2025)
    assert names(board) == ["top", "more_exact", "more_poles", "early", "late"]
    assert [row["rank"] for row in board["results"]] == [1, 2, 3, 4, 5]
    assert board["count"] == 5


def test_season_totals_sum_rounds_and_count_exact_podiums(drivers, clock):
    r1, _, _ = make_weekend(2025, 1, quali_start=NOW)
    r2, _, _ = make_weekend(2025, 2, quali_start=NOW)
    a, b = make_user("a"), make_user("b")
    direct(a, r1, drivers, 25, exact=3, pole_hit=True, podium=True)
    direct(a, r2, drivers, 5, exact=1)
    direct(b, r1, drivers, 20, exact=2)
    board = selectors.leaderboard(season=2025)
    assert board["results"][0] | {"rank": 1} == {
        "rank": 1,
        "user_id": a.pk,
        "name": "a",
        "points": 30,
        "exact_hits": 4,
        "pole_hits": 1,
        "exact_podiums": 1,
        "predictions": 2,
    }
    only_r2 = selectors.leaderboard(season=2025, round_number=2)
    assert names(only_r2) == ["a"] and only_r2["results"][0]["points"] == 5


def test_default_season_is_latest_scored_and_unscored_are_skipped(drivers, clock):
    old, _, _ = make_weekend(2024, 1, quali_start=NOW)
    new, _, _ = make_weekend(2025, 1, quali_start=NOW)
    u = make_user("u")
    direct(u, old, drivers, 5)
    direct(make_user("pending"), new, drivers, 1).__class__.objects.filter(round=new).update(
        points=None
    )
    assert selectors.leaderboard()["season"] == 2024
    assert names(selectors.leaderboard()) == ["u"]
    assert selectors.leaderboard(season=2023)["results"] == []


def test_empty_leaderboard(db):
    assert selectors.leaderboard() == {"season": None, "round": None, "count": 0, "results": []}


def test_pagination_keeps_global_rank(drivers, clock):
    round_, _, _ = make_weekend(2025, 1, quali_start=NOW)
    for points in (9, 8, 7):
        direct(make_user(f"p{points}"), round_, drivers, points)
    page = selectors.leaderboard(season=2025, limit=1, offset=1)
    assert names(page) == ["p8"] and page["results"][0]["rank"] == 2 and page["count"] == 3


def test_league_leaderboard_only_members(drivers, clock):
    round_, _, _ = make_weekend(2025, 1, quali_start=NOW)
    owner, friend, outsider = make_user("owner"), make_user("friend"), make_user("outsider")
    league = services.create_league(owner, "L")
    services.join_league(friend, league.invite_code)
    for u, pts in ((owner, 3), (friend, 4), (outsider, 20)):
        direct(u, round_, drivers, pts)
    assert names(selectors.leaderboard(season=2025, league=league)) == ["friend", "owner"]
    assert names(selectors.leaderboard(season=2025)) == ["outsider", "friend", "owner"]


def test_deleted_users_are_shown_as_deleted_user_one_row_each(drivers, clock):
    r1, _, _ = make_weekend(2025, 1, quali_start=NOW)
    r2, _, _ = make_weekend(2025, 2, quali_start=NOW)
    a, b = make_user("a"), make_user("b")
    direct(a, r1, drivers, 10)
    direct(b, r1, drivers, 7)
    direct(b, r2, drivers, 7)
    b.delete()
    board = selectors.leaderboard(season=2025)
    assert names(board) == ["a", "Deleted user", "Deleted user"]
    assert all(row["user_id"] is None for row in board["results"][1:])


def test_user_without_display_name_gets_a_neutral_name(drivers, clock):
    round_, _, _ = make_weekend(2025, 1, quali_start=NOW)
    user = make_user()
    user.display_name = None
    user.save()
    direct(user, round_, drivers, 1)
    assert selectors.leaderboard(season=2025)["results"][0]["name"] == f"Player {user.pk}"


def test_leaderboard_query_count_does_not_grow_with_players(drivers, clock):
    round_, _, _ = make_weekend(2025, 1, quali_start=NOW)

    def measure():
        with CaptureQueriesContext(connection) as ctx:
            selectors.leaderboard(season=2025)
        return len(ctx)

    for i in range(3):
        direct(make_user(), round_, drivers, i)
    small = measure()
    for i in range(30):
        direct(make_user(), round_, drivers, i)
    assert measure() == small
    assert small <= 2


def test_league_leaderboard_query_count_is_constant(drivers, clock):
    round_, _, _ = make_weekend(2025, 1, quali_start=NOW)
    owner = make_user()
    league = services.create_league(owner, "L")
    for _ in range(20):
        u = make_user()
        services.join_league(u, league.invite_code)
        direct(u, round_, drivers, 1)
    with CaptureQueriesContext(connection) as ctx:
        selectors.leaderboard(season=2025, league=league)
    assert len(ctx) <= 2


# --- Privacy: picks of others and statistics -----------------------------------------------------


def test_league_picks_hidden_before_lock(user, drivers, weekend):
    round_, _, _ = weekend
    league = services.create_league(user, "L")
    ref = catalog.find_round(2025, 1)
    with pytest.raises(errors.PicksHidden):
        selectors.league_picks(league, ref)
    with pytest.raises(errors.PicksHidden):
        selectors.pick_stats(ref)
    assert round_.id == ref["id"]


def test_league_picks_visible_after_lock_only_for_members(user, drivers, weekend, clock):
    owner = make_user("owner")
    league = services.create_league(owner, "L")
    services.join_league(user, league.invite_code)
    outsider = make_user("outsider")
    for u in (owner, user, outsider):
        services.submit_prediction(
            u,
            2025,
            1,
            services.PickInput(
                p1=drivers[0].id,
                p2=drivers[1].id,
                p3=drivers[2].id,
                pole=drivers[3].id,
                fastest_lap=drivers[4].id,
            ),  # fmt: skip
        )
    clock.now = NOW + dt.timedelta(hours=2)
    picks = selectors.league_picks(league, catalog.find_round(2025, 1))
    assert sorted(p["name"] for p in picks) == sorted([owner.display_name, user.display_name])
    assert picks[0]["pick"]["p1"]["id"] == drivers[0].id


def test_stats_after_lock(drivers, weekend, clock):
    users = [make_user() for _ in range(4)]
    for index, u in enumerate(users):
        first = drivers[0] if index < 3 else drivers[1]
        second = drivers[1] if index < 3 else drivers[0]
        services.submit_prediction(
            u,
            2025,
            1,
            services.PickInput(
                p1=first.id, p2=second.id, p3=drivers[2].id, pole=first.id, fastest_lap=first.id
            ),
        )
    clock.now = NOW + dt.timedelta(hours=2)
    stats = selectors.pick_stats(catalog.find_round(2025, 1))
    assert stats["total"] == 4
    top = stats["slots"]["p1"][0]
    assert top["driver"]["id"] == drivers[0].id and top["percent"] == 75.0 and top["count"] == 3
    assert stats["slots"]["p1"][1]["percent"] == 25.0
    assert set(stats["slots"]) == {"p1", "p2", "p3", "pole", "fastest_lap"}


def test_stats_with_no_predictions(weekend, clock):
    clock.now = NOW + dt.timedelta(hours=2)
    stats = selectors.pick_stats(catalog.find_round(2025, 1))
    assert stats["total"] == 0 and stats["slots"]["p1"] == []


# --- History, round state, export -----------------------------------------------------------------


def test_history_shows_pick_result_and_points(user, drivers, weekend, clock):
    round_, quali, race = weekend
    services.submit_prediction(
        user, 2025, 1,
        services.PickInput(p1=drivers[0].id, p2=drivers[1].id, p3=drivers[2].id,
                           pole=drivers[3].id, fastest_lap=drivers[4].id),
    )  # fmt: skip
    rows = selectors.history(user)
    assert rows[0]["result"] is None and rows[0]["points"] is None
    set_race_result(race, drivers[:3], pole=drivers[3], fastest_lap=drivers[4], quali=quali,
                    extra=drivers[3:])  # fmt: skip
    services.score_round(round_.id)
    row = selectors.history(user)[0]
    assert row["points"] == 25 and row["round"]["year"] == 2025
    assert row["result"]["p1"]["id"] == drivers[0].id
    assert row["result"]["pole"]["id"] == drivers[3].id
    assert row["pick"]["fastest_lap"]["id"] == drivers[4].id


def test_history_query_count_is_constant(user, drivers, clock):
    def measure():
        with CaptureQueriesContext(connection) as ctx:
            selectors.history(user)
        return len(ctx)

    for n in range(1, 3):
        r, _, _ = make_weekend(2025, n, quali_start=NOW)
        direct(user, r, drivers, 1)
    small = measure()
    for n in range(3, 10):
        r, _, _ = make_weekend(2025, n, quali_start=NOW)
        direct(user, r, drivers, 1)
    assert measure() == small


def test_round_state_open_closed_unavailable(user, drivers, weekend, clock):
    ref = catalog.find_round(2025, 1)
    state = selectors.round_state(user, ref)
    assert state["status"] == "open" and state["closes_at"] == NOW + dt.timedelta(hours=1)
    assert state["my_pick"] is None
    clock.now = NOW + dt.timedelta(hours=2)
    assert selectors.round_state(user, ref)["status"] == "closed"
    other, _, _ = make_weekend(2025, 2, with_quali=False)
    assert selectors.round_state(user, catalog.find_round(2025, 2))["status"] == "unavailable"


def test_my_leagues_lists_member_counts(user):
    league = services.create_league(user, "L")
    services.join_league(make_user(), league.invite_code)
    assert selectors.my_leagues(user) == [
        {"name": "L", "invite_code": league.invite_code, "is_owner": True, "member_count": 2}
    ]


def test_export_contains_predictions_and_leagues(user, drivers, weekend):
    services.submit_prediction(
        user, 2025, 1,
        services.PickInput(p1=drivers[0].id, p2=drivers[1].id, p3=drivers[2].id,
                           pole=drivers[3].id, fastest_lap=drivers[4].id),
    )  # fmt: skip
    services.create_league(user, "L")
    data = exports.export_user_data(user)
    assert data["predictions"][0]["season"] == 2025 and data["predictions"][0]["round"] == 1
    assert data["leagues"][0]["name"] == "L" and data["leagues"][0]["is_owner"] is True


def test_export_registration_tolerates_missing_accounts_hook(monkeypatch):
    monkeypatch.setitem(sys.modules, "apps.accounts.exports", None)  # import raises ImportError
    exports.register()


def test_export_provider_is_registered_when_accounts_exposes_it(monkeypatch):
    calls = []
    fake = types.ModuleType("apps.accounts.exports")
    fake.register_export_provider = lambda name, func: calls.append((name, func))
    monkeypatch.setitem(sys.modules, "apps.accounts.exports", fake)
    exports.register()
    assert calls == [("predictions", exports.export_user_data)]


# --- Catalog selectors appended for this module ------------------------------------------------


def test_catalog_selectors_missing_data_is_none(db):
    round_, _, _ = make_weekend(2025, 1, with_quali=False)
    assert catalog.qualifying_start(round_.id) is None
    assert catalog.race_outcome(round_.id) == {
        "podium": [None, None, None], "pole": None, "fastest_lap": None
    }  # fmt: skip
    assert catalog.find_round(1999, 1) is None
    assert catalog.session_info(0) is None
    assert catalog.driver_labels([]) == {}


def test_catalog_pole_falls_back_to_grid(db):
    round_, _, race = make_weekend(2025, 1, with_quali=False)
    d = make_drivers(3)
    set_race_result(race, d, pole=d[1])
    assert catalog.race_outcome(round_.id)["pole"] == d[1].id
    assert catalog.race_outcome(round_.id)["podium"] == [x.id for x in d]

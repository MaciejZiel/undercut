import datetime as dt

import pytest
from rest_framework.test import APIClient

from apps.predictions import services
from apps.predictions.models import Prediction

from .conftest import NOW
from .factories import make_user, make_weekend, set_race_result

pytestmark = pytest.mark.django_db

ROUND_URL = "/api/v1/predictions/rounds/2025/1/"


def body(d, **over):
    data = {
        "p1": d[0].id, "p2": d[1].id, "p3": d[2].id, "pole": d[3].id, "fastest_lap": d[4].id
    }  # fmt: skip
    return {**data, **over}


# --- Round state and submit ----------------------------------------------------------------------


def test_round_state_is_public(anon, weekend):
    response = anon.get(ROUND_URL)
    assert response.status_code == 200
    assert response.data["status"] == "open"
    assert response.data["my_pick"] is None
    assert response.data["round"]["name"] == "GP 1"


def test_unknown_round_is_404(anon, db):
    assert anon.get("/api/v1/predictions/rounds/2025/9/").status_code == 404


def test_put_requires_authentication(anon, drivers, weekend):
    assert anon.put(ROUND_URL, body(drivers), format="json").status_code in (401, 403)


def test_put_creates_then_updates(api, drivers, weekend):
    created = api.put(ROUND_URL, body(drivers), format="json")
    assert created.status_code == 201
    assert created.data["my_pick"]["p1"]["id"] == drivers[0].id
    updated = api.put(ROUND_URL, body(drivers, pole=drivers[5].id), format="json")
    assert updated.status_code == 200
    assert updated.data["my_pick"]["pole"]["id"] == drivers[5].id
    assert api.get(ROUND_URL).data["my_pick"]["pole"]["id"] == drivers[5].id
    assert Prediction.objects.count() == 1


def test_lock_boundary_over_http(api, user, drivers, clock):
    start = NOW + dt.timedelta(hours=1)
    make_weekend(2025, 1, quali_start=start)
    clock.now = start - dt.timedelta(seconds=1)
    assert api.put(ROUND_URL, body(drivers), format="json").status_code == 201
    clock.now = start + dt.timedelta(seconds=1)
    response = api.put(ROUND_URL, body(drivers, pole=drivers[5].id), format="json")
    assert response.status_code == 403
    assert response.data["code"] == "predictions_locked"
    state = api.get(ROUND_URL).data
    assert state["status"] == "closed" and state["my_pick"]["pole"]["id"] == drivers[3].id


def test_client_clock_is_irrelevant(api, drivers, weekend, clock):
    clock.now = NOW + dt.timedelta(hours=5)
    response = api.put(
        ROUND_URL, body(drivers), format="json", HTTP_DATE="Mon, 01 Jan 2001 00:00:00 GMT"
    )
    assert response.status_code == 403


def test_unverified_email_is_403(drivers, weekend):
    client = APIClient()
    client.force_login(make_user(verified=False))
    response = client.put(ROUND_URL, body(drivers), format="json")
    assert response.status_code == 403 and response.data["code"] == "email_not_verified"


def test_duplicate_drivers_are_400(api, drivers, weekend):
    response = api.put(ROUND_URL, body(drivers, p3=drivers[0].id), format="json")
    assert response.status_code == 400


def test_missing_fields_are_400(api, weekend):
    assert api.put(ROUND_URL, {"p1": 1}, format="json").status_code == 400


def test_unknown_driver_is_400(api, drivers, weekend):
    assert api.put(ROUND_URL, body(drivers, pole=987654), format="json").status_code == 400


def test_no_qualifying_time_is_409(api, drivers, clock):
    make_weekend(2025, 1, with_quali=False)
    response = api.put(ROUND_URL, body(drivers), format="json")
    assert response.status_code == 409 and response.data["code"] == "qualifying_time_unknown"
    assert api.get(ROUND_URL).data["status"] == "unavailable"


def test_csrf_is_enforced_for_session_auth(user, drivers, weekend):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.put(ROUND_URL, body(drivers), format="json").status_code == 403


# --- History, leaderboard, stats ---


def test_history_requires_auth_and_lists_picks(anon, api, drivers, weekend):
    assert anon.get("/api/v1/predictions/history/").status_code in (401, 403)
    api.put(ROUND_URL, body(drivers), format="json")
    rows = api.get("/api/v1/predictions/history/").data
    assert len(rows) == 1 and rows[0]["round"]["round"] == 1


def _score(user, drivers, weekend, clock):
    round_, quali, race = weekend
    services.submit_prediction(
        user, 2025, 1,
        services.PickInput(p1=drivers[0].id, p2=drivers[1].id, p3=drivers[2].id,
                           pole=drivers[3].id, fastest_lap=drivers[4].id),
    )  # fmt: skip
    set_race_result(race, drivers[:3], pole=drivers[3], fastest_lap=drivers[4], quali=quali,
                    extra=drivers[3:])  # fmt: skip
    services.score_round(round_.id)
    clock.now = NOW + dt.timedelta(hours=2)


def test_leaderboard_is_public(anon, user, drivers, weekend, clock):
    _score(user, drivers, weekend, clock)
    response = anon.get("/api/v1/predictions/leaderboard/?season=2025&round=1")
    assert response.status_code == 200
    assert response.data["results"][0]["points"] == 25
    assert response.data["results"][0]["exact_podiums"] == 1


def test_leaderboard_round_requires_season(anon, db):
    assert anon.get("/api/v1/predictions/leaderboard/?round=1").status_code == 400


def test_league_leaderboard_members_only(user, drivers, weekend, clock):
    _score(user, drivers, weekend, clock)
    league = services.create_league(user, "L")
    owner_client = APIClient()
    owner_client.force_login(user)
    url = f"/api/v1/predictions/leaderboard/?season=2025&league={league.invite_code}"
    assert owner_client.get(url).status_code == 200
    outsider = APIClient()
    outsider.force_login(make_user())
    assert outsider.get(url).status_code == 404
    assert APIClient().get(url).status_code == 403
    assert owner_client.get("/api/v1/predictions/leaderboard/?league=NOPE1234").status_code == 404


def test_stats_hidden_then_visible(anon, user, drivers, weekend, clock):
    _score(user, drivers, weekend, clock)
    clock.now = NOW  # before lock
    assert anon.get(ROUND_URL + "stats/").status_code == 403
    clock.now = NOW + dt.timedelta(hours=2)
    response = anon.get(ROUND_URL + "stats/")
    assert response.status_code == 200
    assert response.data["slots"]["p1"][0]["percent"] == 100.0


# --- Leagues -------------------------------------------------------------------------------------


def test_league_lifecycle(api, user, drivers, weekend, clock):
    created = api.post("/api/v1/leagues/", {"name": "Friends"}, format="json")
    assert created.status_code == 201
    code = created.data["invite_code"]
    assert api.get("/api/v1/leagues/").data[0]["name"] == "Friends"

    friend = make_user("friend")
    friend_client = APIClient()
    friend_client.force_login(friend)
    joined = friend_client.post("/api/v1/leagues/join/", {"code": code.lower()}, format="json")
    assert joined.status_code == 200 and joined.data["member_count"] == 2
    assert (
        friend_client.post("/api/v1/leagues/join/", {"code": code}, format="json").status_code
        == 409
    )
    assert friend_client.get(f"/api/v1/leagues/{code}/").status_code == 200

    # picks hidden before the lock, visible after
    picks_url = f"/api/v1/leagues/{code}/rounds/2025/1/picks/"
    friend_client.put(ROUND_URL, body(drivers), format="json")
    assert api.get(picks_url).status_code == 403
    clock.now = NOW + dt.timedelta(hours=2)
    picks = api.get(picks_url)
    assert picks.status_code == 200 and picks.data[0]["name"] == "friend"

    # only the owner manages
    assert friend_client.post(f"/api/v1/leagues/{code}/renew-code/").status_code == 403
    assert friend_client.delete(f"/api/v1/leagues/{code}/members/{user.pk}/").status_code == 403
    renewed = api.post(f"/api/v1/leagues/{code}/renew-code/")
    assert renewed.status_code == 200 and renewed.data["invite_code"] != code
    new_code = renewed.data["invite_code"]
    assert api.get(f"/api/v1/leagues/{code}/").status_code == 404
    assert api.delete(f"/api/v1/leagues/{new_code}/members/{friend.pk}/").status_code == 204
    assert friend_client.get(f"/api/v1/leagues/{new_code}/").status_code == 404
    assert api.delete(f"/api/v1/leagues/{new_code}/members/{friend.pk}/").status_code == 404
    assert api.post(f"/api/v1/leagues/{new_code}/leave/").status_code == 409
    assert api.delete(f"/api/v1/leagues/{new_code}/").status_code == 204


def test_league_limits_over_http(api):
    for i in range(10):
        assert api.post("/api/v1/leagues/", {"name": f"L{i}"}, format="json").status_code == 201
    response = api.post("/api/v1/leagues/", {"name": "x"}, format="json")
    assert response.status_code == 409 and response.data["code"] == "league_limit_reached"


def test_league_writes_need_auth(anon):
    assert anon.post("/api/v1/leagues/", {"name": "x"}, format="json").status_code in (401, 403)
    assert anon.post("/api/v1/leagues/join/", {"code": "x"}, format="json").status_code in (
        401,
        403,
    )


def test_non_member_cannot_see_league_or_picks(api, user, weekend, clock):
    other = make_user()
    league = services.create_league(other, "Secret")
    code = league.invite_code
    assert api.get(f"/api/v1/leagues/{code}/").status_code == 404
    clock.now = NOW + dt.timedelta(hours=2)
    assert api.get(f"/api/v1/leagues/{code}/rounds/2025/1/picks/").status_code == 404


def test_deleted_user_in_league_leaderboard_is_gone_from_league_but_global_shows_label(
    user, drivers, weekend, clock
):
    _score(user, drivers, weekend, clock)
    user.delete()
    response = APIClient().get("/api/v1/predictions/leaderboard/?season=2025")
    assert response.data["results"][0]["name"] == "Deleted user"

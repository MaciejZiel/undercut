import datetime as dt

import pytest
from django.db import IntegrityError, transaction

from apps.events.models import OutboxEvent
from apps.predictions import errors, handlers, services
from apps.predictions.models import League, LeagueMembership, Prediction

from .conftest import NOW
from .factories import make_user, make_weekend, set_race_result

pytestmark = pytest.mark.django_db


def pick(d, **over):
    base = {"p1": d[0].id, "p2": d[1].id, "p3": d[2].id, "pole": d[3].id, "fastest_lap": d[4].id}
    return services.PickInput(**{**base, **over})


# --- Lock -------------------------------------------------------------------------------------


def test_submit_one_second_before_lock_is_ok(user, drivers, clock):
    start = NOW + dt.timedelta(hours=1)
    make_weekend(2025, 1, quali_start=start)
    clock.now = start - dt.timedelta(seconds=1)
    prediction, created = services.submit_prediction(user, 2025, 1, pick(drivers))
    assert created and prediction.pk


def test_submit_one_second_after_lock_is_rejected(user, drivers, clock):
    start = NOW + dt.timedelta(hours=1)
    make_weekend(2025, 1, quali_start=start)
    clock.now = start + dt.timedelta(seconds=1)
    with pytest.raises(errors.PredictionsLocked):
        services.submit_prediction(user, 2025, 1, pick(drivers))


def test_lock_instant_itself_is_locked(user, drivers, clock):
    start = NOW + dt.timedelta(hours=1)
    make_weekend(2025, 1, quali_start=start)
    clock.now = start
    with pytest.raises(errors.PredictionsLocked):
        services.submit_prediction(user, 2025, 1, pick(drivers))


def test_update_after_lock_is_rejected(user, drivers, weekend, clock):
    services.submit_prediction(user, 2025, 1, pick(drivers))
    clock.now = NOW + dt.timedelta(hours=2)
    with pytest.raises(errors.PredictionsLocked):
        services.submit_prediction(user, 2025, 1, pick(drivers, pole=drivers[5].id))


def test_lock_follows_a_changed_qualifying_time(user, drivers, weekend):
    _, quali, _ = weekend
    quali.start_utc = NOW - dt.timedelta(minutes=1)
    quali.save()
    with pytest.raises(errors.PredictionsLocked):
        services.submit_prediction(user, 2025, 1, pick(drivers))
    quali.start_utc = NOW + dt.timedelta(days=1)
    quali.save()
    services.submit_prediction(user, 2025, 1, pick(drivers))


def test_missing_qualifying_session_is_a_clear_error(user, drivers, clock):
    make_weekend(2025, 1, with_quali=False)
    with pytest.raises(errors.QualifyingTimeUnknown):
        services.submit_prediction(user, 2025, 1, pick(drivers))


def test_qualifying_without_start_time_is_a_clear_error(user, drivers, clock):
    make_weekend(2025, 1, quali_start=None)
    with pytest.raises(errors.QualifyingTimeUnknown):
        services.submit_prediction(user, 2025, 1, pick(drivers))


def test_unknown_round(user, drivers):
    with pytest.raises(errors.RoundNotFound):
        services.submit_prediction(user, 2025, 9, pick(drivers))


def test_cancelled_round(user, drivers, weekend):
    round_, _, _ = weekend
    round_.is_cancelled = True
    round_.save()
    with pytest.raises(errors.RoundCancelled):
        services.submit_prediction(user, 2025, 1, pick(drivers))


# --- Submit rules ------------------------------------------------------------------------------


def test_requires_verified_email(drivers, weekend):
    with pytest.raises(errors.EmailNotVerified):
        services.submit_prediction(make_user(verified=False), 2025, 1, pick(drivers))


def test_duplicate_podium_driver_is_rejected(user, drivers, weekend):
    with pytest.raises(errors.InvalidPrediction):
        services.submit_prediction(user, 2025, 1, pick(drivers, p2=drivers[0].id))


def test_pole_and_fastest_lap_may_repeat_podium_drivers(user, drivers, weekend):
    services.submit_prediction(
        user, 2025, 1, pick(drivers, pole=drivers[0].id, fastest_lap=drivers[0].id)
    )


def test_unknown_driver_is_rejected(user, drivers, weekend):
    with pytest.raises(errors.InvalidPrediction):
        services.submit_prediction(user, 2025, 1, pick(drivers, pole=999999))


def test_resubmit_updates_instead_of_duplicating(user, drivers, weekend):
    first, created = services.submit_prediction(user, 2025, 1, pick(drivers))
    second, created2 = services.submit_prediction(user, 2025, 1, pick(drivers, pole=drivers[5].id))
    assert created and not created2
    assert first.pk == second.pk
    assert Prediction.objects.count() == 1
    assert Prediction.objects.get().pole_id == drivers[5].id


# --- Database constraints ------------------------------------------------------------------------


def test_db_blocks_duplicate_user_round(user, drivers, weekend):
    round_, _, _ = weekend
    kwargs = dict(
        round=round_, p1=drivers[0], p2=drivers[1], p3=drivers[2], pole=drivers[3],
        fastest_lap=drivers[4],
    )  # fmt: skip
    Prediction.objects.create(user=user, **kwargs)
    with pytest.raises(IntegrityError), transaction.atomic():
        Prediction.objects.create(user=user, **kwargs)


def test_db_allows_many_deleted_user_predictions_for_one_round(drivers, weekend):
    round_, _, _ = weekend
    kwargs = dict(
        round=round_, p1=drivers[0], p2=drivers[1], p3=drivers[2], pole=drivers[3],
        fastest_lap=drivers[4],
    )  # fmt: skip
    Prediction.objects.create(user=None, **kwargs)
    Prediction.objects.create(user=None, **kwargs)
    assert Prediction.objects.count() == 2


@pytest.mark.parametrize("dup", [("p1", "p2"), ("p1", "p3"), ("p2", "p3")])
def test_db_blocks_duplicate_podium_drivers(user, drivers, weekend, dup):
    round_, _, _ = weekend
    fields = dict(p1=drivers[0], p2=drivers[1], p3=drivers[2])
    fields[dup[1]] = fields[dup[0]]
    with pytest.raises(IntegrityError), transaction.atomic():
        Prediction.objects.create(
            user=user, round=round_, pole=drivers[3], fastest_lap=drivers[4], **fields
        )


def test_deleting_the_account_keeps_the_prediction(user, drivers, weekend):
    services.submit_prediction(user, 2025, 1, pick(drivers))
    user.delete()
    prediction = Prediction.objects.get()
    assert prediction.user is None


# --- Scoring service -----------------------------------------------------------------------------


def _scored_setup(user, drivers, weekend):
    round_, quali, race = weekend
    services.submit_prediction(user, 2025, 1, pick(drivers))
    set_race_result(
        race,
        drivers[:3],
        pole=drivers[3],
        fastest_lap=drivers[4],
        quali=quali,
        extra=drivers[3:],
    )
    return round_, quali, race


def test_score_round_scores_all_predictions(user, drivers, weekend):
    round_, _, _ = _scored_setup(user, drivers, weekend)
    other = make_user()
    services.submit_prediction(other, 2025, 1, pick(drivers, p1=drivers[1].id, p2=drivers[0].id))
    assert services.score_round(round_.id) == 2
    mine = Prediction.objects.get(user=user)
    theirs = Prediction.objects.get(user=other)
    assert mine.points == 25
    assert mine.breakdown["exact_podium"] is True
    assert theirs.points == 2 + 2 + 5 + 3 + 2


def test_score_round_without_results_leaves_points_null(user, drivers, weekend):
    round_, _, _ = weekend
    services.submit_prediction(user, 2025, 1, pick(drivers))
    services.score_round(round_.id)
    prediction = Prediction.objects.get()
    assert prediction.points is None and prediction.breakdown == {}


def test_rescore_is_idempotent(user, drivers, weekend):
    round_, _, _ = _scored_setup(user, drivers, weekend)
    services.score_round(round_.id)
    first = Prediction.objects.values("points", "breakdown").get()
    services.score_round(round_.id)
    assert Prediction.objects.values("points", "breakdown").get() == first


def test_rescore_after_disqualification_correction(user, drivers, weekend):
    round_, quali, race = _scored_setup(user, drivers, weekend)
    services.score_round(round_.id)
    assert Prediction.objects.get().points == 25
    # drivers[0] disqualified: result reshuffled, pole/fastest lap unchanged
    set_race_result(
        race, [drivers[1], drivers[2], drivers[5]], pole=drivers[3], fastest_lap=drivers[4],
        quali=quali, extra=[drivers[0], drivers[3], drivers[4]],
    )  # fmt: skip
    services.score_round(round_.id)
    corrected = Prediction.objects.get()
    assert corrected.points == 0 + 2 + 2 + 3 + 2
    assert corrected.breakdown["exact_hits"] == 0
    services.score_round(round_.id)
    assert Prediction.objects.get().points == corrected.points


def test_disqualified_driver_position_text_d_is_ignored(user, drivers, weekend):
    from django.apps import apps

    round_, quali, race = _scored_setup(user, drivers, weekend)
    apps.get_model("catalog", "Result").objects.filter(session=race, driver=drivers[0]).update(
        position_text="D"
    )
    services.score_round(round_.id)
    prediction = Prediction.objects.get()
    assert prediction.breakdown["p1"] is None
    assert prediction.points == 5 + 5 + 3 + 2


def test_resubmit_clears_stale_points(user, drivers, weekend):
    round_, _, _ = _scored_setup(user, drivers, weekend)
    services.score_round(round_.id)
    services.submit_prediction(user, 2025, 1, pick(drivers, pole=drivers[5].id))
    assert Prediction.objects.get().points is None


# --- Handlers ------------------------------------------------------------------------------------


class Event:
    def __init__(self, payload):
        self.payload = payload


def test_race_finalized_scores_and_publishes(user, drivers, weekend):
    round_, _, race = _scored_setup(user, drivers, weekend)
    handlers.on_session_results_finalized(Event({"session_id": race.id, "version": 1}))
    assert Prediction.objects.get().points == 25
    event = OutboxEvent.objects.get(type="PredictionsScored")
    assert event.key == f"round:{round_.id}"
    assert event.payload == {"round_id": round_.id}


def test_race_finalized_twice_is_safe(user, drivers, weekend):
    _, _, race = _scored_setup(user, drivers, weekend)
    for _ in range(2):
        handlers.on_session_results_finalized(Event({"session_id": race.id}))
    assert Prediction.objects.get().points == 25


def test_non_race_session_is_ignored(user, drivers, weekend):
    _, quali, _ = _scored_setup(user, drivers, weekend)
    handlers.on_session_results_finalized(Event({"session_id": quali.id}))
    assert Prediction.objects.get().points is None
    assert not OutboxEvent.objects.exists()


def test_unknown_session_is_ignored(db):
    handlers.on_session_results_finalized(Event({"session_id": 424242}))
    assert not OutboxEvent.objects.exists()


def test_predictions_closed_is_a_noop(db):
    assert handlers.on_predictions_closed(Event({"round_id": 1})) is None


def test_handlers_are_registered_by_the_app():
    from apps.events import registry

    handlers.register_handlers()
    assert handlers.on_session_results_finalized in registry.handlers_for("SessionResultsFinalized")
    assert handlers.on_predictions_closed in registry.handlers_for("PredictionsClosed")


# --- Leagues -------------------------------------------------------------------------------------


def test_create_league_makes_owner_a_member(user):
    league = services.create_league(user, " Friends ")
    assert league.name == "Friends"
    assert len(league.invite_code) == 8
    assert league.owner == user
    assert LeagueMembership.objects.filter(league=league, user=user).exists()


def test_league_name_required(user):
    with pytest.raises(errors.InvalidPrediction):
        services.create_league(user, "  ")


def test_max_ten_leagues_per_user(user):
    for i in range(10):
        services.create_league(user, f"L{i}")
    with pytest.raises(errors.LeagueLimitReached):
        services.create_league(user, "one too many")
    other = make_user()
    league = services.create_league(other, "x")
    with pytest.raises(errors.LeagueLimitReached):
        services.join_league(user, league.invite_code)


def test_join_by_code_case_insensitive_and_idempotency(user):
    league = services.create_league(make_user(), "L")
    services.join_league(user, league.invite_code.lower())
    with pytest.raises(errors.AlreadyMember):
        services.join_league(user, league.invite_code)


def test_join_unknown_code(user):
    with pytest.raises(errors.LeagueNotFound):
        services.join_league(user, "NOPE1234")


def test_league_limit_50_members(user):
    owner = make_user()
    league = services.create_league(owner, "Big")
    for _ in range(49):
        LeagueMembership.objects.create(league=league, user=make_user())
    assert league.memberships.count() == 50
    with pytest.raises(errors.LeagueFull):
        services.join_league(user, league.invite_code)


def test_owner_removes_member_and_others_cannot(user):
    owner, member, stranger = make_user(), user, make_user()
    league = services.create_league(owner, "L")
    services.join_league(member, league.invite_code)
    services.join_league(stranger, league.invite_code)
    with pytest.raises(errors.NotLeagueOwner):
        services.remove_member(member, league.invite_code, stranger.pk)
    services.remove_member(owner, league.invite_code, member.pk)
    assert not LeagueMembership.objects.filter(league=league, user=member).exists()
    with pytest.raises(errors.NotLeagueMember):
        services.remove_member(owner, league.invite_code, member.pk)
    with pytest.raises(errors.OwnerCannotLeave):
        services.remove_member(owner, league.invite_code, owner.pk)


def test_renew_code_invalidates_old_one(user):
    owner = make_user()
    league = services.create_league(owner, "L")
    old = league.invite_code
    renewed = services.renew_code(owner, old)
    assert renewed.invite_code != old
    with pytest.raises(errors.LeagueNotFound):
        services.join_league(user, old)
    services.join_league(user, renewed.invite_code)
    with pytest.raises(errors.NotLeagueOwner):
        services.renew_code(user, renewed.invite_code)


def test_leave_and_delete(user):
    owner = make_user()
    league = services.create_league(owner, "L")
    services.join_league(user, league.invite_code)
    services.leave_league(user, league.invite_code)
    with pytest.raises(errors.NotLeagueMember):
        services.leave_league(user, league.invite_code)
    with pytest.raises(errors.OwnerCannotLeave):
        services.leave_league(owner, league.invite_code)
    with pytest.raises(errors.NotLeagueOwner):
        services.delete_league(user, league.invite_code)
    services.delete_league(owner, league.invite_code)
    assert not League.objects.exists()


def test_ownerless_league_cannot_be_managed(user):
    owner = make_user()
    league = services.create_league(owner, "L")
    services.join_league(user, league.invite_code)
    owner.delete()
    with pytest.raises(errors.NotLeagueOwner):
        services.renew_code(user, league.invite_code)


def test_invite_code_db_constraints(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        League.objects.create(name="x", owner=user, invite_code="short")

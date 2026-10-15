import datetime as dt

import pytest
from django.core.management import call_command

from apps.accounts import demo, handlers, services
from apps.accounts import selectors_public as accounts_public
from apps.events import registry
from apps.events.publisher import publish
from apps.events.worker import process_batch
from apps.predictions import selectors
from apps.predictions.models import Prediction
from tests.catalog.factories import (
    ConstructorFactory,
    DriverFactory,
    ResultFactory,
    RoundFactory,
    SeasonFactory,
    SessionFactory,
)

from .conftest import NOW
from .factories import make_user

pytestmark = pytest.mark.django_db
TODAY = dt.date(2025, 3, 14)


@pytest.fixture
def world(clock):
    """Two finished rounds with 12 drivers each and an open round 3 (qualifying tomorrow)."""
    season = SeasonFactory(year=2025)
    team = ConstructorFactory()
    drivers = [DriverFactory() for _ in range(12)]
    rounds = []
    for number, day in ((1, 2), (2, 9)):
        round_ = RoundFactory(season=season, round=number, date=dt.date(2025, 3, day))
        race = SessionFactory(round=round_, type="RACE", status="results_final")
        quali = SessionFactory(round=round_, type="Q", status="results_final")
        for index, driver in enumerate(drivers, start=1):
            ResultFactory(
                session=race,
                driver=driver,
                constructor=team,
                position=index,
                position_text=str(index),
                grid=index,
                fastest_lap_rank=1 if index == 4 else None,
            )
        quali.qualifying_results.create(driver=drivers[0], constructor=team, position=1)
        rounds.append(round_)
    open_round = RoundFactory(season=season, round=3, date=dt.date(2025, 3, 30))
    SessionFactory(
        round=open_round, type="Q", start_utc=NOW + dt.timedelta(days=1), status="scheduled"
    )
    return {"rounds": rounds, "open": open_round, "drivers": drivers}


@pytest.fixture
def demo_user(world):
    call_command("seed_demo_user")
    return services.get_demo_user()


def snapshot():
    return sorted(
        (p.user_id, p.round_id, p.p1_id, p.p2_id, p.p3_id, p.pole_id, p.fastest_lap_id, p.points)
        for p in Prediction.objects.all()
    )


def bots():
    return services.User.objects.filter(username__startswith=demo.BOT_USERNAME_PREFIX)


def test_reset_builds_bots_league_and_sample_picks(demo_user, world):
    demo.reset_demo_data(TODAY)

    assert bots().count() == 8
    for bot in bots():
        assert bot.is_demo and not bot.has_usable_password()
        assert bot.email == "" and not bot.email_verified
    # Last completed round (scored) and the open round (unscored) for every bot.
    last, previous = world["rounds"][1], world["rounds"][0]
    for bot in bots():
        assert bot.predictions.get(round=last).points is not None
        assert bot.predictions.get(round=world["open"]).points is None
        assert bot.predictions.count() == 2
    assert sorted(demo_user.predictions.values_list("round_id", flat=True)) == [
        previous.pk,
        last.pk,
    ]
    assert all(p.points is not None for p in demo_user.predictions.all())
    league = demo_user.owned_leagues.get()
    assert league.invite_code == demo.DEMO_LEAGUE_CODE
    assert league.memberships.count() == 9


def test_league_ranking_is_never_empty(demo_user, world):
    demo.reset_demo_data(TODAY)
    league = demo_user.owned_leagues.get()
    ranking = selectors.leaderboard(league=league)
    assert ranking["count"] == 9


def test_reset_is_idempotent(demo_user, world):
    demo.reset_demo_data(TODAY)
    first = snapshot()
    users = services.User.objects.count()
    demo.reset_demo_data(TODAY)
    demo.reset_demo_data(TODAY)
    assert snapshot() == first
    assert services.User.objects.count() == users
    assert demo_user.owned_leagues.count() == 1
    assert demo_user.owned_leagues.get().memberships.count() == 9


def test_picks_are_reproducible_from_the_date(demo_user, world):
    demo.reset_demo_data(TODAY)
    same_day = snapshot()
    demo.reset_demo_data(TODAY + dt.timedelta(days=1))
    other_day = snapshot()
    demo.reset_demo_data(TODAY)
    assert snapshot() == same_day
    assert other_day != same_day


def test_reset_restores_the_demo_account_and_leaves_real_users_alone(demo_user, world):
    real = make_user()
    real.predictions.create(
        round=world["rounds"][1],
        p1=world["drivers"][0],
        p2=world["drivers"][1],
        p3=world["drivers"][2],
        pole=world["drivers"][0],
        fastest_lap=world["drivers"][0],
        points=7,
    )
    demo_user.predictions.create(
        round=world["open"],
        p1=world["drivers"][0],
        p2=world["drivers"][1],
        p3=world["drivers"][2],
        pole=world["drivers"][0],
        fastest_lap=world["drivers"][0],
    )

    demo.reset_demo_data(TODAY)

    assert not demo_user.predictions.filter(round=world["open"]).exists()
    assert real.predictions.get().points == 7


def test_without_a_demo_user_nothing_happens(world):
    demo.reset_demo_data(TODAY)
    assert bots().count() == 0 and Prediction.objects.count() == 0


def test_without_finished_rounds_only_the_league_is_built(clock):
    call_command("seed_demo_user")
    demo.reset_demo_data(TODAY)
    assert bots().count() == 8 and Prediction.objects.count() == 0


def test_bot_name_taken_by_a_real_user_does_not_break_the_reset(demo_user, world):
    make_user("Demo Bot Alpha")
    demo.reset_demo_data(TODAY)
    assert bots().count() == 8
    assert bots().filter(display_name__isnull=True).count() == 1


def test_demo_accounts_are_known_to_other_modules(demo_user, world):
    demo.reset_demo_data(TODAY)
    ids = accounts_public.demo_user_ids()
    assert demo_user.pk in ids and set(bots().values_list("pk", flat=True)) <= ids
    assert len(ids) == 9


def test_handler_runs_the_whole_reset_through_the_outbox(demo_user, world):
    registry.clear()
    handlers.register_handlers()
    publish("DemoResetDue", key="demo-reset", payload={"slot": "2025-03-14T03:00:00Z"})
    assert process_batch() == 1
    assert bots().count() == 8
    assert demo_user.predictions.count() == 2


def test_demo_and_bots_stay_out_of_the_global_leaderboard(demo_user, world):
    demo.reset_demo_data(TODAY)
    real = make_user()
    real.predictions.create(
        round=world["rounds"][1],
        p1=world["drivers"][0],
        p2=world["drivers"][1],
        p3=world["drivers"][2],
        pole=world["drivers"][0],
        fastest_lap=world["drivers"][0],
        points=5,
    )
    ranking = selectors.leaderboard(season=2025)
    assert [row["user_id"] for row in ranking["results"]] == [real.pk]

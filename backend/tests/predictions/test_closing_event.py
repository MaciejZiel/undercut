import datetime as dt

import pytest

from apps.events.models import OutboxEvent
from apps.events.scheduler import run_due
from apps.predictions import handlers
from tests.catalog.factories import RoundFactory, SeasonFactory, SessionFactory

pytestmark = pytest.mark.django_db

START = dt.datetime(2024, 3, 1, 16, 0, tzinfo=dt.UTC)


@pytest.fixture
def qualifying():
    round_ = RoundFactory(season=SeasonFactory(year=2024), round=1)
    return SessionFactory(round=round_, type="Q", start_utc=START)


def test_event_fires_once_when_qualifying_starts(qualifying):
    assert (
        run_due(START - dt.timedelta(seconds=1), schedule=[], providers=[handlers.closing_due]) == 0
    )
    assert (
        run_due(START + dt.timedelta(seconds=1), schedule=[], providers=[handlers.closing_due]) == 1
    )
    assert (
        run_due(START + dt.timedelta(minutes=30), schedule=[], providers=[handlers.closing_due])
        == 0
    )
    event = OutboxEvent.objects.get()
    assert (event.type, event.key) == ("PredictionsClosed", f"round:{qualifying.round_id}")
    assert event.payload == {"round_id": qualifying.round_id}


def test_a_missed_tick_is_caught_up_but_not_forever(qualifying):
    assert (
        run_due(START + dt.timedelta(hours=5), schedule=[], providers=[handlers.closing_due]) == 1
    )


def test_old_qualifying_sessions_are_not_replayed(qualifying):
    assert (
        run_due(START + dt.timedelta(hours=7), schedule=[], providers=[handlers.closing_due]) == 0
    )


def test_a_rescheduled_qualifying_fires_again(qualifying):
    run_due(START + dt.timedelta(minutes=1), schedule=[], providers=[handlers.closing_due])
    qualifying.start_utc = START + dt.timedelta(hours=1)
    qualifying.save()
    assert (
        run_due(
            START + dt.timedelta(hours=1, minutes=1), schedule=[], providers=[handlers.closing_due]
        )
        == 1
    )


def test_cancelled_rounds_do_not_close(qualifying):
    qualifying.round.is_cancelled = True
    qualifying.round.save()
    assert (
        run_due(START + dt.timedelta(minutes=1), schedule=[], providers=[handlers.closing_due]) == 0
    )

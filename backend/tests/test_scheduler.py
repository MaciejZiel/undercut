from datetime import UTC, datetime

import pytest

from apps.events.models import OutboxEvent
from apps.events.scheduler import Recurring, run_due

DAILY = Recurring("daily", "DailyDue", hour=5)
WEEKLY = Recurring("weekly", "WeeklyDue", hour=6, weekday=0)  # Monday


def at(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=UTC)


def test_daily_slot_is_today_when_time_has_passed():
    assert DAILY.latest_slot(at(2026, 10, 15, 9)) == at(2026, 10, 15, 5)


def test_daily_slot_is_yesterday_when_time_not_reached():
    assert DAILY.latest_slot(at(2026, 10, 15, 4, 59)) == at(2026, 10, 14, 5)


def test_weekly_slot_is_the_last_monday():
    # 2026-10-15 is a Thursday, the last Monday was 2026-10-12
    assert WEEKLY.latest_slot(at(2026, 10, 15, 9)) == at(2026, 10, 12, 6)


def test_weekly_slot_on_monday_before_the_hour_is_previous_monday():
    assert WEEKLY.latest_slot(at(2026, 10, 12, 5, 30)) == at(2026, 10, 5, 6)


@pytest.mark.django_db
def test_run_due_publishes_once_per_slot():
    now = at(2026, 10, 15, 9)
    assert run_due(now, [DAILY]) == 1
    assert run_due(now, [DAILY]) == 0  # re-running within the same slot is a no-op
    assert run_due(at(2026, 10, 15, 23), [DAILY]) == 0

    event = OutboxEvent.objects.get()
    assert event.type == "DailyDue"
    assert event.payload == {"slot": "2026-10-15T05:00:00+00:00"}


@pytest.mark.django_db
def test_run_due_fires_again_on_the_next_slot():
    run_due(at(2026, 10, 15, 9), [DAILY])
    assert run_due(at(2026, 10, 16, 9), [DAILY]) == 1
    assert OutboxEvent.objects.count() == 2

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import Circuit, Round, Season, Session
from apps.events.models import OutboxEvent
from apps.ops import heartbeat as hb
from apps.ops.models import Heartbeat


@pytest.fixture(autouse=True)
def _reset_ops_state():
    hb._last_write.clear()
    from apps.ops import views

    views._migrations_ok_until = 0.0
    yield
    hb._last_write.clear()


@pytest.fixture
def healthy_heartbeats(db):
    for name in hb.EXPECTED:
        Heartbeat.objects.create(name=name, beat_at=timezone.now())


@pytest.fixture
def make_race(db):
    counter = iter(range(1, 1000))

    def make(*, ended_ago: timedelta, status=Session.Status.FINISHED, end_known=True):
        n = next(counter)
        season, _ = Season.objects.get_or_create(year=2026)
        circuit = Circuit.objects.create(slug=f"c{n}", name=f"Circuit {n}")
        rnd = Round.objects.create(
            season=season, round=n, name=f"Grand Prix {n}", circuit=circuit, date="2026-03-01"
        )
        end = timezone.now() - ended_ago
        return Session.objects.create(
            round=rnd,
            type=Session.Type.RACE,
            start_utc=end - timedelta(hours=2),
            end_utc=end if end_known else None,
            status=status,
        )

    return make


@pytest.fixture
def make_event(db):
    def make(status=OutboxEvent.Status.PENDING, age=timedelta(0), type="Ping", key=""):
        event = OutboxEvent.objects.create(type=type, key=key, status=status)
        OutboxEvent.objects.filter(pk=event.pk).update(created_at=timezone.now() - age)
        return event

    return make

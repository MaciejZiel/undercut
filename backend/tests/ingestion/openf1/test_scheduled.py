import datetime as dt
from types import SimpleNamespace

import pytest

from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.scheduler import run_due
from apps.events.worker import process_batch
from apps.ingestion import handlers
from apps.ingestion.models import SyncRun
from tests.catalog.factories import RoundFactory, SeasonFactory, SessionFactory

pytestmark = pytest.mark.django_db

END = dt.datetime(2024, 11, 23, 8, 0, tzinfo=dt.UTC)


@pytest.fixture
def race():
    rnd = RoundFactory(season=SeasonFactory(year=2024), round=22)
    return SessionFactory(
        round=rnd, type="RACE", start_utc=END - dt.timedelta(hours=2), end_utc=END
    )


def due_ids(now):
    return [e.payload["session_id"] for e in handlers.analytics_due(now)]


def test_analytics_become_due_two_hours_after_the_end(race):
    assert due_ids(END + dt.timedelta(hours=1, minutes=59)) == []
    assert due_ids(END + dt.timedelta(hours=2)) == [race.id]


def test_analytics_stop_being_due_after_a_day(race):
    assert due_ids(END + dt.timedelta(hours=24, minutes=1)) == []


def test_only_races_and_sprints_are_imported():
    rnd = RoundFactory(season=SeasonFactory(year=2024), round=3)
    for kind in ("Q", "FP1", "SQ"):
        SessionFactory(round=rnd, type=kind, end_utc=END)
    assert due_ids(END + dt.timedelta(hours=3)) == []


def test_sprint_is_included():
    rnd = RoundFactory(season=SeasonFactory(year=2024), round=5)
    sprint = SessionFactory(round=rnd, type="SPRINT", end_utc=END)
    assert due_ids(END + dt.timedelta(hours=3)) == [sprint.id]


def test_cancelled_rounds_are_skipped(race):
    race.round.is_cancelled = True
    race.round.save()
    assert due_ids(END + dt.timedelta(hours=3)) == []


def test_one_event_per_two_hour_slot(race):
    t = END + dt.timedelta(hours=2, minutes=5)  # 10:05 UTC, slot 10:00
    assert run_due(t, schedule=[], providers=[handlers.analytics_due]) == 1
    assert (
        run_due(t + dt.timedelta(minutes=40), schedule=[], providers=[handlers.analytics_due]) == 0
    )
    assert run_due(t + dt.timedelta(hours=2), schedule=[], providers=[handlers.analytics_due]) == 1
    assert OutboxEvent.objects.filter(type="AnalyticsDue").count() == 2


# --------------------------------------------------------------------------- handler


def fake_import(status=SyncRun.Status.SUCCESS, errors=()):
    calls = []

    def run_import(client, **kwargs):
        calls.append(kwargs)
        run = SyncRun.objects.create(
            source="openf1", job="import_openf1", status=status, errors=list(errors)
        )
        return SimpleNamespace(run=run)

    return run_import, calls


@pytest.fixture(autouse=True)
def no_real_client(monkeypatch):
    monkeypatch.setattr(handlers, "OpenF1Client", lambda: object())


def due_event(session):
    return publish("AnalyticsDue", key=f"session:{session.id}", payload={"session_id": session.id})


def test_handler_imports_exactly_that_session(race, monkeypatch):
    run_import, calls = fake_import()
    monkeypatch.setattr(handlers, "run_import", run_import)
    handlers.on_analytics_due(due_event(race))
    assert calls == [
        {
            "years": [2024],
            "round_number": 22,
            "types": frozenset({"RACE"}),
            "force": False,
            "dry_run": False,
        }
    ]


def test_seasons_before_2023_are_ignored(monkeypatch):
    run_import, calls = fake_import()
    monkeypatch.setattr(handlers, "run_import", run_import)
    old = SessionFactory(round=RoundFactory(season=SeasonFactory(year=2022), round=1), type="RACE")
    handlers.on_analytics_due(due_event(old))
    assert calls == []


def test_a_failed_import_is_retried_through_the_outbox(race, monkeypatch):
    registered = handlers.on_analytics_due
    run_import, _ = fake_import(status=SyncRun.Status.FAILED)
    monkeypatch.setattr(handlers, "run_import", run_import)
    with pytest.raises(RuntimeError, match="failed"):
        registered(due_event(race))


def test_unmatched_drivers_are_reported_but_do_not_fail_the_event(race, monkeypatch, caplog):
    run_import, _ = fake_import(
        status=SyncRun.Status.PARTIAL, errors=[{"type": "unmatched_driver"}]
    )
    monkeypatch.setattr(handlers, "run_import", run_import)
    with caplog.at_level("WARNING"):
        handlers.on_analytics_due(due_event(race))
    assert "1 problem" in caplog.text


def test_worker_runs_the_handler(race, monkeypatch):
    from apps.events import registry

    registry.clear()
    handlers.register()
    run_import, calls = fake_import()
    monkeypatch.setattr(handlers, "run_import", run_import)
    event = due_event(race)

    process_batch()

    event.refresh_from_db()
    assert event.status == "done" and len(calls) == 1
    registry.clear()

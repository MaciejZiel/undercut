import datetime as dt

import pytest

from apps.catalog.models import Session
from apps.events import registry
from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.scheduler import run_due
from apps.events.worker import process_batch
from apps.ingestion import handlers
from apps.ingestion.jolpica import sync

from . import data as d

pytestmark = pytest.mark.django_db

NOW = dt.datetime(2024, 3, 2, 20, 0, tzinfo=dt.UTC)  # five hours after the Bahrain race start


@pytest.fixture(autouse=True)
def registered_handlers():
    registry.clear()
    handlers.register()
    yield
    registry.clear()


@pytest.fixture
def season():
    sync.sync_calendar(d.FakeClient(schedule=d.schedule(d.BAHRAIN)), 2024)
    return Session.objects.get(round__round=1, type="RACE")


def due_ids(now):
    return [e.payload["session_id"] for e in handlers.results_due(now)]


def test_results_become_due_one_hour_after_the_session_ends(season):
    ends = season.end_utc
    assert due_ids(ends + dt.timedelta(minutes=59)) == []
    assert due_ids(ends + dt.timedelta(hours=1)) == [season.id]


def test_results_stop_being_due_after_twelve_hours_or_once_final(season):
    ends = season.end_utc
    assert due_ids(ends + dt.timedelta(hours=12, minutes=1)) == []
    Session.objects.filter(pk=season.pk).update(status="results_final")
    assert due_ids(ends + dt.timedelta(hours=2)) == []


def test_scheduler_fires_one_results_event_per_hour(season):
    at = season.end_utc + dt.timedelta(hours=2, minutes=10)
    assert run_due(at, schedule=[], providers=[handlers.results_due]) == 1
    assert (
        run_due(at + dt.timedelta(minutes=5), schedule=[], providers=[handlers.results_due]) == 0
    )  # same hour
    assert (
        run_due(at + dt.timedelta(hours=1), schedule=[], providers=[handlers.results_due]) == 1
    )  # next hourly poll
    assert OutboxEvent.objects.filter(type="SessionResultsDue").count() == 2


def test_worker_turns_a_due_event_into_results_and_standings(season, monkeypatch):
    client = d.FakeClient(
        results=d.results(d.result_row(1, "1", d.VER, d.RED_BULL, 26)),
        driver_standings=d.driver_standings((1, "26", 1, d.VER)),
        constructor_standings=d.constructor_standings((1, "26", 1, d.RED_BULL)),
    )
    monkeypatch.setattr(handlers, "shared_client", lambda: client)
    publish("SessionResultsDue", key=f"session:{season.id}", payload={"session_id": season.id})

    process_batch()

    types = set(OutboxEvent.objects.values_list("type", flat=True))
    assert {"SessionResultsFinalized", "StandingsUpdated"} <= types
    assert Session.objects.get(pk=season.pk).status == "results_final"
    assert ("driver_standings", 2024, 1) in client.calls


def test_failing_source_is_retried_through_the_outbox(season, monkeypatch):
    class Down(d.FakeClient):
        def results(self, year, number):
            raise RuntimeError("down")

    monkeypatch.setattr(handlers, "shared_client", lambda: Down())
    event = publish("SessionResultsDue", key="session:1", payload={"session_id": season.id})

    process_batch()

    event.refresh_from_db()
    assert event.status == "pending" and event.attempts == 1 and "down" in event.last_error


def test_calendar_event_refreshes_the_current_season(season, monkeypatch):
    client = d.FakeClient(schedule=d.schedule(d.BAHRAIN))
    monkeypatch.setattr(handlers, "shared_client", lambda: client)
    monkeypatch.setattr(handlers.timezone, "localdate", lambda: dt.date(2024, 3, 1))
    publish("CalendarSyncDue", key="calendar-sync", payload={})

    process_batch()

    assert client.calls == [("schedule", 2024)]


def test_corrections_event_resyncs_the_latest_finished_round(season, monkeypatch):
    client = d.FakeClient(
        results=d.results(d.result_row(1, "1", d.VER, d.RED_BULL, 26)),
        qualifying=d.qualifying(d.quali_row(1, d.VER, d.RED_BULL, "1:30.0")),
        driver_standings=d.driver_standings((1, "26", 1, d.VER)),
        constructor_standings=d.constructor_standings((1, "26", 1, d.RED_BULL)),
    )
    monkeypatch.setattr(handlers, "shared_client", lambda: client)
    monkeypatch.setattr(handlers.timezone, "now", lambda: season.end_utc + dt.timedelta(days=2))
    publish("ResultsCorrectionsDue", key="results-corrections", payload={})

    process_batch()

    assert {name for name, *_ in client.calls} == {
        "results",
        "qualifying",
        "driver_standings",
        "constructor_standings",
    }


def catchup_ids(now):
    return [e.payload["session_id"] for e in handlers.results_catchup_due(now)]


def test_a_missed_session_is_retried_once_a_day_for_a_month(season):
    ends = season.end_utc
    assert season.id not in catchup_ids(ends + dt.timedelta(hours=11))  # hourly polls cover it
    assert season.id in catchup_ids(ends + dt.timedelta(days=3))
    assert season.id not in catchup_ids(ends + dt.timedelta(days=31))
    Session.objects.filter(pk=season.pk).update(status="results_final")
    assert season.id not in catchup_ids(ends + dt.timedelta(days=3))


def test_the_catch_up_fires_once_per_day(season):
    at = season.end_utc + dt.timedelta(days=3, hours=2)
    first = run_due(at, schedule=[], providers=[handlers.results_catchup_due])
    assert first >= 1
    later = at + dt.timedelta(hours=1)
    assert run_due(later, schedule=[], providers=[handlers.results_catchup_due]) == 0

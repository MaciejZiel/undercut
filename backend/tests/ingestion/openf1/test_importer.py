import datetime as dt
import io

import pytest
from django.core.management import CommandError, call_command

from apps.analytics.models import (
    IntervalSample,
    Lap,
    PitStop,
    PositionSample,
    RaceControlMessage,
    Stint,
    WeatherSample,
)
from apps.catalog.models import Round, Session
from apps.events.models import OutboxEvent
from apps.ingestion.models import DriverNumberMap, SyncRun
from apps.ingestion.openf1 import importer
from apps.ingestion.openf1.client import OpenF1Error, ResponseTooLarge

from .conftest import NOW, RACE_KEY, T0, FakeClient

pytestmark = pytest.mark.django_db

TABLES = [Lap, Stint, PitStop, PositionSample, IntervalSample, RaceControlMessage, WeatherSample]


def counts():
    return {m.__name__: m.objects.count() for m in TABLES}


def run(client, **kwargs):
    kwargs.setdefault("years", [2024])
    kwargs.setdefault("now", NOW)
    return importer.run_import(client, **kwargs)


def events():
    return OutboxEvent.objects.filter(type="AnalyticsImported")


def test_imports_the_race(bahrain, client):
    summary = run(client, types=frozenset({"RACE"}))
    run_row = summary.run
    assert summary.imported and len(summary.imported) == 1
    assert counts() == {
        "Lap": 12,
        "Stint": 12,
        "PitStop": 1,
        "PositionSample": 30,
        "IntervalSample": 30,
        "RaceControlMessage": 10,
        "WeatherSample": 4,
    }
    lap = Lap.objects.get(driver=bahrain["drivers"]["VER"], lap_number=1)
    assert lap.duration_ms == 97759 and lap.session_id == bahrain["race"].pk
    # 16 drivers of the grid are not in the catalog: reported, never guessed
    assert run_row.status == SyncRun.Status.PARTIAL
    assert sum(e["type"] == "unmatched_driver" for e in run_row.errors) == 16
    assert DriverNumberMap.objects.count() == 4
    assert str(RACE_KEY) in run_row.scope["done"]
    assert run_row.scope["requests"] == client.requests
    # 2 for matching + 6 plain endpoints + position (4 windows) + intervals (3 windows)
    assert client.requests == 2 + 6 + 4 + 3
    assert summary.by_endpoint["position"] == 4
    [event] = events()
    assert event.key == f"session:{bahrain['race'].pk}"
    assert event.payload == {"session_id": bahrain["race"].pk}


def test_requests_are_windowed(bahrain, client):
    run(client, types=frozenset({"RACE"}))
    windows = [p for e, p in client.calls if e == "position"]
    assert windows[0]["date>="] == "2024-03-02T13:30:00"
    assert windows[-1]["date<"] == "2024-03-02T17:10:00"
    assert all("session_key" in p and "date<" in p for p in windows)


def test_window_halves_when_the_response_is_too_large():
    def hook(endpoint, params, c):
        start = dt.datetime.fromisoformat(params["date>="])
        stop = dt.datetime.fromisoformat(params["date<"])
        if stop - start > dt.timedelta(minutes=20):
            raise ResponseTooLarge("big")

    c = FakeClient(hook=hook)
    start = T0
    rows = importer.fetch_windowed(c, "position", RACE_KEY, start, start + dt.timedelta(minutes=60))
    assert len(rows) == 30  # everything in the fixture falls in the first 6 minutes
    assert c.requests == 7  # 60 -> 2x30 -> 4x15 minutes


def test_second_run_is_skipped_and_writes_nothing(bahrain, client):
    run(client, types=frozenset({"RACE"}))
    before = counts()
    second_client = FakeClient()
    second = run(second_client, types=frozenset({"RACE"}))
    assert counts() == before
    assert second.skipped == {"already imported": [second.skipped["already imported"][0]]}
    assert second_client.requests == 2  # only meetings and sessions
    assert events().count() == 1
    assert second.run.status == SyncRun.Status.SUCCESS or second.run.errors  # no new data errors


def test_force_reimports_to_the_same_rows(bahrain, client):
    run(client, types=frozenset({"RACE"}))
    before = counts()
    forced = run(FakeClient(), types=frozenset({"RACE"}), force=True)
    assert len(forced.imported) == 1
    assert counts() == before
    assert forced.rows["race_control_new"] == 0
    assert events().count() == 2  # one event per import of the session


def test_resume_after_a_failed_session(bahrain):
    laps_calls = []

    def hook(endpoint, params, c):
        if endpoint == "laps":
            laps_calls.append(1)
            if len(laps_calls) == 2:  # the qualifying goes first, the race is the second
                raise OpenF1Error("HTTP 500", status=500)

    first = run(FakeClient(hook=hook))
    assert len(first.imported) == 1
    failed = [e for e in first.run.errors if e["type"] == "session_failed"]
    assert len(failed) == 1 and f"key {RACE_KEY}" in failed[0]["session"]
    assert Lap.objects.filter(session=bahrain["race"]).count() == 0  # nothing half written
    assert Lap.objects.filter(session=bahrain["quali"]).count() == 12

    client = FakeClient()
    second = run(client)
    assert len(second.imported) == 1 and f"key {RACE_KEY}" in second.imported[0]
    assert second.skipped["already imported"] == [first.imported[0]]
    assert Lap.objects.filter(session=bahrain["race"]).count() == 12
    assert client.by_endpoint["laps"] == 1


def test_dry_run_rolls_everything_back(bahrain, client):
    summary = run(client, types=frozenset({"RACE"}), dry_run=True)
    assert sum(summary.rows.values()) > 0  # it did the work...
    assert counts() == {m.__name__: 0 for m in TABLES}  # ...and undid it
    assert not events().exists()
    assert DriverNumberMap.objects.count() == 0
    assert Round.objects.get(pk=bahrain["round"].pk).openf1_meeting_key is None
    assert Session.objects.get(pk=bahrain["race"].pk).openf1_session_key is None
    assert SyncRun.objects.get(pk=summary.run.pk).scope["dry_run"] is True
    # a dry run is not progress: the real run still imports the session
    real = run(FakeClient(), types=frozenset({"RACE"}))
    assert len(real.imported) == 1 and Lap.objects.count() == 12


def test_unfinished_session_is_not_imported(bahrain, client):
    Session.objects.filter(pk=bahrain["race"].pk).update(status="scheduled")
    summary = run(client, types=frozenset({"RACE"}), now=T0 + dt.timedelta(minutes=30))
    # OpenF1 says the session ends 17:00, so at 15:30 it is still running
    assert summary.skipped == {"not finished": [summary.skipped["not finished"][0]]}
    assert client.by_endpoint["laps"] == 0 and Lap.objects.count() == 0


def test_session_key_and_round_selection(bahrain):
    c = FakeClient()
    summary = importer.run_import(c, session_key=9468, now=NOW)
    assert len(summary.imported) == 1 and "Q" in summary.imported[0]
    assert Lap.objects.filter(session=bahrain["quali"]).exists()
    assert not Lap.objects.filter(session=bahrain["race"]).exists()
    assert c.by_endpoint["position"] == 0  # qualifying has no race-like series
    other = run(FakeClient(), round_number=2)
    assert other.imported == []


def test_unknown_session_key_is_reported(bahrain, client):
    summary = importer.run_import(client, session_key=1, now=NOW)
    assert summary.run.errors[0]["type"] == "unknown_session"


def test_aborts_after_repeated_failures(bahrain):
    def hook(endpoint, params, c):
        if endpoint == "drivers":
            raise OpenF1Error("down")

    importer.MAX_CONSECUTIVE_FAILURES, saved = 2, importer.MAX_CONSECUTIVE_FAILURES
    try:
        summary = run(FakeClient(hook=hook))
    finally:
        importer.MAX_CONSECUTIVE_FAILURES = saved
    assert summary.run.status == SyncRun.Status.FAILED
    assert summary.run.errors[-1]["type"] == "aborted"


# --------------------------------------------------------------------------- the command


@pytest.fixture
def patched_client(monkeypatch):
    holder = {}

    def factory():
        holder["client"] = FakeClient()
        return holder["client"]

    monkeypatch.setattr("apps.ingestion.management.commands.import_openf1.OpenF1Client", factory)
    return holder


def test_command_prints_a_summary(bahrain, patched_client):
    out, err = io.StringIO(), io.StringIO()
    call_command("import_openf1", "--year", "2024", "--types", "RACE", stdout=out, stderr=err)
    text = out.getvalue()
    assert "sessions imported: 1" in text
    assert "requests: 15" in text and "position=4" in text
    assert "lap" in text and "unmatched_driver" in err.getvalue()
    assert Lap.objects.count() == 12


def test_command_round_dry_run(bahrain, patched_client):
    out = io.StringIO()
    call_command("import_openf1", "--round", "2024:1", "--dry-run", stdout=out)
    assert "dry run, rolled back" in out.getvalue()
    assert Lap.objects.count() == 0


@pytest.mark.parametrize(
    "args", [["--round", "2024"], ["--year", "2020"], ["--year", "2024", "--types", "XX"]]
)
def test_command_rejects_bad_arguments(args, patched_client):
    with pytest.raises(CommandError):
        call_command("import_openf1", *args)

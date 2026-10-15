import datetime as dt

import pytest

from apps.catalog.models import QualifyingResult, Result, Round, Session
from apps.events.models import OutboxEvent
from apps.ingestion.jolpica import sync
from apps.ingestion.models import SyncRun
from apps.standings.models import ConstructorStanding, DriverStanding

from . import data as d

pytestmark = pytest.mark.django_db

NOW = dt.datetime(2024, 3, 2, 20, 0, tzinfo=dt.UTC)


def events(event_type):
    return list(OutboxEvent.objects.filter(type=event_type))


def calendar_client(*races):
    return d.FakeClient(schedule=d.schedule(*races))


def race_session():
    return Session.objects.get(round__round=1, type="RACE")


@pytest.fixture
def season():
    sync.sync_calendar(calendar_client(d.BAHRAIN, d.CHINA), 2024)


def race_client(*rows, **extra):
    return d.FakeClient(results=d.results(*rows), **extra)


# --------------------------------------------------------------------------- calendar


def test_calendar_creates_rounds_circuits_and_session_times():
    run = sync.sync_calendar(calendar_client(d.BAHRAIN, d.CHINA), 2024)

    assert run.status == SyncRun.Status.SUCCESS and run.errors == []
    assert Round.objects.filter(season__year=2024).count() == 2
    qualifying = Session.objects.get(round__round=1, type="Q")
    assert qualifying.start_utc == dt.datetime(2024, 3, 1, 16, 0, tzinfo=dt.UTC)
    assert qualifying.end_utc == dt.datetime(2024, 3, 1, 17, 0, tzinfo=dt.UTC)
    assert Session.objects.filter(round__round=5, type="SQ").exists()


def test_calendar_is_idempotent():
    sync.sync_calendar(calendar_client(d.BAHRAIN), 2024)
    run = sync.sync_calendar(calendar_client(d.BAHRAIN), 2024)
    assert (run.created, run.updated) == (0, 0)


def test_calendar_refresh_never_downgrades_a_session_with_results(season):
    Session.objects.filter(round__round=1, type="RACE").update(status="results_final")

    sync.sync_calendar(calendar_client(d.BAHRAIN, d.CHINA), 2024)

    assert race_session().status == "results_final"


def test_calendar_marks_vanished_rounds_cancelled_but_keeps_them(season):
    run = sync.sync_calendar(calendar_client(d.BAHRAIN), 2024)  # China is gone from the source

    china = Round.objects.get(season__year=2024, round=5)
    assert china.is_cancelled
    assert run.status == SyncRun.Status.PARTIAL
    assert run.errors[0]["rounds"] == [5]


def test_empty_schedule_is_an_outage_not_a_mass_cancellation(season):
    sync.sync_calendar(calendar_client(), 2024)
    assert not Round.objects.filter(is_cancelled=True).exists()


# --------------------------------------------------------------------------- results


def test_results_are_stored_and_published_once(season):
    client = race_client(
        d.result_row(1, "1", d.VER, d.RED_BULL, 26, rank=1),
        d.result_row(2, "2", d.SAI, d.FERRARI, 18, grid="2", millis="5510000"),
    )

    first = sync.sync_session_results(client, race_session().id, now=NOW)
    second = sync.sync_session_results(client, race_session().id, now=NOW)

    assert first.available and first.changed
    assert not second.changed  # nothing new: no second event
    assert Result.objects.filter(session=race_session()).count() == 2
    assert race_session().status == "results_final"
    [event] = events("SessionResultsFinalized")
    assert event.key == f"session:{race_session().id}"
    assert event.payload["session_id"] == race_session().id
    winner = Result.objects.get(session=race_session(), position=1)
    assert (winner.constructor.jolpica_id, winner.points, winner.fastest_lap_rank) == (
        "red_bull",
        26,
        1,
    )


def test_new_drivers_and_constructors_are_created_from_the_response(season):
    sync.sync_session_results(
        race_client(d.result_row(1, "1", d.VER, d.RED_BULL, 25)), race_session().id, now=NOW
    )
    driver = Result.objects.get().driver
    assert (driver.code, driver.family_name, driver.permanent_number) == ("VER", "Verstappen", 1)


def test_a_late_penalty_republishes_the_event(season):
    sync.sync_session_results(
        race_client(
            d.result_row(1, "1", d.VER, d.RED_BULL, 25), d.result_row(2, "2", d.SAI, d.FERRARI, 18)
        ),
        race_session().id,
        now=NOW,
    )
    corrected = race_client(
        d.result_row(1, "1", d.SAI, d.FERRARI, 25),
        d.result_row(2, "D", d.VER, d.RED_BULL, 0, status="Disqualified"),
    )

    result = sync.sync_session_results(corrected, race_session().id, now=NOW + dt.timedelta(days=2))

    assert result.changed
    assert len(events("SessionResultsFinalized")) == 2
    assert Result.objects.get(driver__code="VER").position_text == "D"


def test_results_not_published_yet_change_nothing(season):
    result = sync.sync_session_results(
        d.FakeClient(results=d.results()), race_session().id, now=NOW
    )
    assert not result.available and not result.changed
    assert race_session().status != "results_final"
    assert not events("SessionResultsFinalized")


def test_manual_override_survives_a_sync(season):
    sync.sync_session_results(
        race_client(d.result_row(1, "1", d.VER, d.RED_BULL, 25)), race_session().id, now=NOW
    )
    Result.objects.update(points=99, manual_override=True)

    run_client = race_client(d.result_row(1, "1", d.VER, d.RED_BULL, 25))
    sync.sync_session_results(run_client, race_session().id, now=NOW)

    assert Result.objects.get().points == 99
    assert SyncRun.objects.filter(job="session-results").latest("id").skipped == 1


def test_qualifying_session_uses_the_qualifying_endpoint(season):
    q = Session.objects.get(round__round=1, type="Q")
    client = d.FakeClient(
        qualifying=d.qualifying(
            d.quali_row(1, d.VER, d.RED_BULL, "1:30.031", "1:29.374", "1:29.179")
        )
    )

    sync.sync_session_results(client, q.id, now=NOW)

    assert client.calls == [("qualifying", 2024, 1)]
    row = QualifyingResult.objects.get(session=q)
    assert (row.driver.code, row.q1_ms, row.q3_ms) == ("VER", 90031, 89179)


def test_failure_is_recorded_and_raised(season):
    class Boom(d.FakeClient):
        def results(self, year, number):
            raise RuntimeError("source down")

    with pytest.raises(RuntimeError):
        sync.sync_session_results(Boom(), race_session().id, now=NOW)
    run = SyncRun.objects.filter(job="session-results").latest("id")
    assert run.status == SyncRun.Status.FAILED and "source down" in run.errors[0]["error"]


def test_sessions_without_a_synced_type_are_ignored(season):
    fp1 = Session.objects.get(round__round=1, type="FP1")
    result = sync.sync_session_results(d.FakeClient(), fp1.id, now=NOW)
    assert not result.available


# --------------------------------------------------------------------------- standings


def standings_client():
    return d.FakeClient(
        driver_standings=d.driver_standings((1, "26", 1, d.VER), (2, "18", 0, d.SAI)),
        constructor_standings=d.constructor_standings(
            (1, "26", 1, d.RED_BULL), (2, "18", 0, d.FERRARI)
        ),
    )


def test_standings_are_stored_with_podiums_from_results(season):
    sync.sync_session_results(
        race_client(
            d.result_row(1, "1", d.VER, d.RED_BULL, 26), d.result_row(2, "2", d.SAI, d.FERRARI, 18)
        ),
        race_session().id,
        now=NOW,
    )

    sync.sync_standings(standings_client(), 2024, 1)

    ver = DriverStanding.objects.get(driver__code="VER")
    assert (ver.position, ver.points, ver.wins, ver.podiums, ver.after_round) == (1, 26, 1, 1, 1)
    assert ConstructorStanding.objects.get(constructor__jolpica_id="ferrari").position == 2
    assert len(events("StandingsUpdated")) == 1


def test_unchanged_standings_publish_nothing_new(season):
    sync.sync_session_results(
        race_client(d.result_row(1, "1", d.VER, d.RED_BULL, 26)), race_session().id, now=NOW
    )
    sync.sync_standings(standings_client(), 2024, 1)
    sync.sync_standings(standings_client(), 2024, 1)
    assert len(events("StandingsUpdated")) == 1


def test_standings_for_an_unknown_season_fail_clearly():
    with pytest.raises(LookupError, match="2024"):
        sync.sync_standings(standings_client(), 2024, 1)

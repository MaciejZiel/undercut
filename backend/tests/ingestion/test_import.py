import datetime as dt
import io
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.catalog.models import (
    Circuit,
    Constructor,
    ConstructorSeason,
    Driver,
    QualifyingResult,
    Result,
    Round,
    Season,
    Session,
)
from apps.events.models import OutboxEvent
from apps.ingestion.jolpica.importer import run_import
from apps.ingestion.models import SyncRun

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "dump"
TODAY = dt.date(2024, 1, 1)


def test_import_creates_the_catalog():
    run, totals = run_import(FIXTURES, today=TODAY)
    assert run.status == SyncRun.Status.SUCCESS
    assert (run.created, run.updated, run.skipped, run.errors) == (run.created, 0, 0, [])
    assert Season.objects.count() == 2
    assert Circuit.objects.count() == 3
    assert Driver.objects.count() == 3  # Farina has no team entry in the fixture seasons
    assert Constructor.objects.count() == 3
    assert ConstructorSeason.objects.count() == 5
    assert Round.objects.count() == 3
    assert Session.objects.count() == 2 + 4 and totals["session"].created == 6
    assert Result.objects.count() == 3 + 3 + 2
    assert QualifyingResult.objects.count() == 3 + 3 + 3
    assert Driver.objects.get(jolpica_id="leclerc").code == "LEC"
    assert (
        ConstructorSeason.objects.get(constructor__slug="red-bull", season__year=2022).color_hex
        == "#3671c6"
    )


def test_cancelled_round_is_kept_without_number():
    run_import(FIXTURES, today=TODAY)
    cancelled = Round.objects.get(is_cancelled=True)
    assert cancelled.round is None and cancelled.season.year == 2023
    assert cancelled.sessions.count() == 0


def test_qualifying_is_stored_as_one_merged_row_per_driver():
    run_import(FIXTURES, today=TODAY)
    row = QualifyingResult.objects.get(
        session__round__season__year=2022, session__type="Q", driver__code="LEC"
    )
    assert (row.position, row.q1_ms, row.q2_ms, row.q3_ms) == (2, 88000, 87000, 85000)


def test_result_keeps_team_on_race_day():
    run_import(FIXTURES, today=TODAY)
    race = Result.objects.get(
        session__type="RACE", session__round__season__year=2023, driver__code="HAM"
    )
    assert race.constructor.jolpica_id == "ferrari"
    assert race.position_text == "3" or race.position_text == "D"
    dnf = Result.objects.get(
        session__round__season__year=2022, driver__code="LEC", session__type="RACE"
    )
    assert (dnf.position_text, dnf.status, dnf.best_lap_ms) == ("R", "Engine", None)


def test_second_run_creates_nothing():
    run_import(FIXTURES, today=TODAY)
    run, totals = run_import(FIXTURES, today=TODAY)
    assert run.created == 0 and run.updated == 0 and run.skipped == 0
    assert all(c.created == 0 and c.updated == 0 for c in totals.values())
    assert totals["result"].unchanged == 8
    assert Result.objects.count() == 8


def test_changed_source_row_is_updated_not_duplicated():
    run_import(FIXTURES, today=TODAY)
    Result.objects.filter(driver__code="VER", session__round__season__year=2022).update(points=0)
    run, totals = run_import(FIXTURES, today=TODAY)
    assert totals["result"].updated == 1 and run.created == 0
    assert Result.objects.get(driver__code="VER", session__round__season__year=2022).points == 25


def test_manual_override_is_never_overwritten():
    run_import(FIXTURES, today=TODAY)
    locked = Result.objects.get(driver__code="VER", session__round__season__year=2022)
    locked.points = 99
    locked.manual_override = True
    locked.save()
    run, totals = run_import(FIXTURES, today=TODAY)
    locked.refresh_from_db()
    assert locked.points == 99
    assert totals["result"].skipped_manual == 1
    assert run.skipped == 1


def test_dry_run_changes_nothing_but_reports_counts():
    run, totals = run_import(FIXTURES, dry_run=True, today=TODAY)
    assert totals["result"].created == 8
    assert Season.objects.count() == 0 and Result.objects.count() == 0
    assert OutboxEvent.objects.count() == 0
    stored = SyncRun.objects.get(pk=run.pk)
    assert stored.scope["dry_run"] is True and stored.status == SyncRun.Status.SUCCESS


def test_year_range_limits_the_import():
    run_import(FIXTURES, from_year=2023, to_year=2023, today=TODAY)
    assert list(Season.objects.values_list("year", flat=True)) == [2023]
    assert Round.objects.count() == 2


def test_event_is_published_once_per_successful_import():
    run, _ = run_import(FIXTURES, today=TODAY)
    event = OutboxEvent.objects.get(type="HistoryImported")
    assert event.payload["sync_run_id"] == run.pk and event.payload["rounds"] == 3


def test_failed_round_is_recorded_and_the_rest_imported(monkeypatch):
    from apps.catalog import services

    original = services.upsert_results

    def flaky(session_id, rows):
        if any(r.driver_jolpica_id == "hamilton" and r.position == 1 for r in rows):
            raise RuntimeError("boom")
        return original(session_id, rows)

    monkeypatch.setattr(services, "upsert_results", flaky)
    # the 2023 sprint puts Verstappen first, so make the failure hit the 2022 race instead
    monkeypatch.setattr(
        services,
        "upsert_results",
        lambda sid, rows: (
            (_ for _ in ()).throw(RuntimeError("boom"))
            if Session.objects.get(pk=sid).round.season.year == 2022
            and Session.objects.get(pk=sid).type == "RACE"
            else original(sid, rows)
        ),
    )
    run, _ = run_import(FIXTURES, today=TODAY)
    assert run.status == SyncRun.Status.PARTIAL
    assert len(run.errors) == 1 and "boom" in run.errors[0]["error"]
    assert Round.objects.filter(season__year=2022).count() == 0  # that round rolled back as a unit
    assert Round.objects.filter(season__year=2023).count() == 2


def test_management_command_with_zip(tmp_path):
    import zipfile

    archive = tmp_path / "dump.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for p in FIXTURES.glob("*.csv"):
            z.write(p, p.name)
    out = io.StringIO()
    call_command("import_history", dump=archive, stdout=out)
    assert "result" in out.getvalue() and "created=8" in out.getvalue()
    out = io.StringIO()
    call_command("import_history", dump=FIXTURES, stdout=out)
    assert "created=0" in out.getvalue()
    assert SyncRun.objects.count() == 2

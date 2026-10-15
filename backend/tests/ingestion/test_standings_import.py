import datetime as dt
from pathlib import Path

import pytest

from apps.ingestion.jolpica.importer import run_import
from apps.ingestion.models import SyncRun
from apps.standings.models import ConstructorStanding, DriverStanding

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "dump"
TODAY = dt.date(2024, 1, 1)


def standing(year, after_round, code):
    return DriverStanding.objects.get(season__year=year, after_round=after_round, driver__code=code)


def test_standings_are_imported_after_races_only():
    run, totals = run_import(FIXTURES, today=TODAY)

    assert run.status == SyncRun.Status.SUCCESS and run.errors == []
    # 2022 R1: three eligible drivers (the ineligible one is dropped); 2023 R1: three entries
    assert DriverStanding.objects.count() == 3 + 3
    assert ConstructorStanding.objects.count() == 3 + 2
    assert totals["driver_standing"].created == 6


def test_sprint_snapshot_does_not_replace_the_race_table():
    run_import(FIXTURES, today=TODAY)
    row = standing(2023, 1, "VER")
    assert (row.points, row.position, row.wins) == (33, 1, 1)  # not the 8 points after the sprint


def test_eligible_entry_without_a_position_is_kept_with_null_position():
    run_import(FIXTURES, today=TODAY)
    row = standing(2023, 1, "HAM")
    assert row.position is None and row.position_text == ""


def test_podiums_count_classified_finishes_only():
    run_import(FIXTURES, today=TODAY)
    assert standing(2022, 1, "VER").podiums == 1
    assert standing(2022, 1, "HAM").podiums == 1
    assert standing(2022, 1, "LEC").podiums == 0  # third on the grid sheet but retired
    assert standing(2023, 1, "HAM").podiums == 0  # disqualified
    assert standing(2023, 1, "LEC").podiums == 1


def test_second_run_changes_nothing():
    run_import(FIXTURES, today=TODAY)
    before = list(DriverStanding.objects.order_by("pk").values_list("pk", "points"))

    _, totals = run_import(FIXTURES, today=TODAY)

    assert totals["driver_standing"].created == 0
    assert list(DriverStanding.objects.order_by("pk").values_list("pk", "points")) == before


def test_year_filter_limits_the_standings():
    run_import(FIXTURES, from_year=2023, to_year=2023, today=TODAY)
    assert set(DriverStanding.objects.values_list("season__year", flat=True)) == {2023}

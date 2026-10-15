import datetime as dt

import pytest
from django.db import IntegrityError, transaction

from apps.catalog.models import Driver, Result, Session
from apps.catalog.text import make_search_name

from . import factories as f

pytestmark = pytest.mark.django_db


def fails():
    return pytest.raises(IntegrityError)


def test_search_name_strips_diacritics():
    assert make_search_name("Sergio", "Pérez") == "sergio perez"
    assert make_search_name("Nico", "Hülkenberg") == "nico hulkenberg"
    assert make_search_name("Łukasz", "Kubica") == "lukasz kubica"
    assert make_search_name("  Kimi ", "", "Räikkönen") == "kimi raikkonen"


def test_driver_save_sets_search_name_and_slug():
    driver = Driver.objects.create(given_name="Sergio", family_name="Pérez")
    assert driver.search_name == "sergio perez"
    assert driver.slug == "sergio-perez"


def test_driver_has_no_team_or_total_points():
    names = {field.name for field in Driver._meta.get_fields()}
    assert "team" not in names
    assert "constructor" not in names
    assert "total_points" not in names


def test_driver_slug_unique():
    f.DriverFactory(slug="same")
    with fails(), transaction.atomic():
        f.DriverFactory(slug="same")


def test_driver_jolpica_id_unique_but_blank_allowed():
    f.DriverFactory(jolpica_id="")
    f.DriverFactory(jolpica_id="")
    f.DriverFactory(jolpica_id="max_verstappen")
    with fails(), transaction.atomic():
        f.DriverFactory(jolpica_id="max_verstappen")


def test_season_year_unique():
    f.SeasonFactory(year=2025)
    with fails(), transaction.atomic():
        f.SeasonFactory(year=2025)


def test_points_system_unique_per_season_and_type():
    season = f.SeasonFactory()
    f.PointsSystemFactory(season=season, session_type="race")
    f.PointsSystemFactory(season=season, session_type="sprint")
    with fails(), transaction.atomic():
        f.PointsSystemFactory(season=season, session_type="race")


def test_points_system_type_must_be_valid():
    with fails(), transaction.atomic():
        f.PointsSystemFactory(session_type="quali")


def test_round_unique_per_season():
    season = f.SeasonFactory()
    f.RoundFactory(season=season, round=1)
    f.RoundFactory(round=1)  # a different season is fine
    with fails(), transaction.atomic():
        f.RoundFactory(season=season, round=1)


def test_round_number_must_be_positive():
    with fails(), transaction.atomic():
        f.RoundFactory(round=0)


def test_round_can_be_cancelled_and_kept():
    rnd = f.RoundFactory()
    assert rnd.is_cancelled is False
    rnd.is_cancelled = True
    rnd.save()
    rnd.refresh_from_db()
    assert rnd.is_cancelled is True


def test_session_unique_per_round_and_type():
    rnd = f.RoundFactory()
    f.SessionFactory(round=rnd, type=Session.Type.RACE)
    f.SessionFactory(round=rnd, type=Session.Type.Q)
    with fails(), transaction.atomic():
        f.SessionFactory(round=rnd, type=Session.Type.RACE)


def test_session_invalid_type_and_status_rejected():
    with fails(), transaction.atomic():
        f.SessionFactory(type="XYZ")
    with fails(), transaction.atomic():
        f.SessionFactory(status="cancelled")


def test_session_end_must_be_after_start():
    start = dt.datetime(2025, 3, 16, 14, tzinfo=dt.UTC)
    f.SessionFactory(start_utc=start, end_utc=start + dt.timedelta(hours=2))
    with fails(), transaction.atomic():
        f.SessionFactory(type=Session.Type.FP1, start_utc=start, end_utc=start)


def test_session_defaults_to_scheduled():
    assert f.SessionFactory().status == Session.Status.SCHEDULED


def test_result_driver_unique_per_session():
    result = f.ResultFactory()
    with fails(), transaction.atomic():
        f.ResultFactory(session=result.session, driver=result.driver)


def test_result_position_unique_per_session():
    result = f.ResultFactory(position=1)
    with fails(), transaction.atomic():
        f.ResultFactory(session=result.session, position=1)


def test_result_null_positions_may_repeat():
    session = f.SessionFactory()
    f.ResultFactory(session=session, position=None, position_text="R")
    f.ResultFactory(session=session, position=None, position_text="D")
    assert Result.objects.filter(session=session, position__isnull=True).count() == 2


def test_result_position_must_be_positive():
    with fails(), transaction.atomic():
        f.ResultFactory(position=0)


def test_single_fastest_lap_per_session():
    session = f.SessionFactory()
    f.ResultFactory(session=session, fastest_lap_rank=1)
    f.ResultFactory(session=session, fastest_lap_rank=2)
    f.ResultFactory(session=session, fastest_lap_rank=None)
    with fails(), transaction.atomic():
        f.ResultFactory(session=session, fastest_lap_rank=1)
    # another session may have its own fastest lap
    f.ResultFactory(fastest_lap_rank=1)


def test_fastest_lap_rank_must_be_positive():
    with fails(), transaction.atomic():
        f.ResultFactory(fastest_lap_rank=0)


def test_result_points_cannot_be_negative():
    with fails(), transaction.atomic():
        f.ResultFactory(points=-1)


def test_result_manual_override_defaults_false():
    result = f.ResultFactory()
    assert result.manual_override is False
    assert result.source_updated_at is None


def test_result_keeps_historical_constructor_after_driver_changes_team():
    driver = f.DriverFactory()
    old_team = f.ConstructorFactory(name="Old Team")
    new_team = f.ConstructorFactory(name="New Team")
    season = f.SeasonFactory()
    first = f.ResultFactory(
        session=f.SessionFactory(round=f.RoundFactory(season=season, round=1)),
        driver=driver,
        constructor=old_team,
    )
    # The driver moves mid-season: later results carry the new team.
    second = f.ResultFactory(
        session=f.SessionFactory(round=f.RoundFactory(season=season, round=2)),
        driver=driver,
        constructor=new_team,
    )
    driver.refresh_from_db()
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.constructor == old_team
    assert second.constructor == new_team
    teams = list(
        Result.objects.filter(driver=driver)
        .order_by("session__round__round")
        .values_list("constructor__name", flat=True)
    )
    assert teams == ["Old Team", "New Team"]


def test_constructor_season_unique():
    cs = f.ConstructorSeasonFactory()
    with fails(), transaction.atomic():
        f.ConstructorSeasonFactory(constructor=cs.constructor, season=cs.season)


def test_circuit_slug_unique():
    f.CircuitFactory(slug="monza")
    with fails(), transaction.atomic():
        f.CircuitFactory(slug="monza")


def test_qualifying_unique_driver_and_position_per_session():
    q = f.QualifyingResultFactory(position=1)
    with fails(), transaction.atomic():
        f.QualifyingResultFactory(session=q.session, driver=q.driver, position=2)
    with fails(), transaction.atomic():
        f.QualifyingResultFactory(session=q.session, position=1)
    f.QualifyingResultFactory(session=q.session, position=None)
    f.QualifyingResultFactory(session=q.session, position=None)


def test_str_methods():
    result = f.ResultFactory()
    for obj in (
        result,
        result.session,
        result.session.round,
        result.driver,
        result.constructor,
        result.session.round.season,
        result.session.round.circuit,
        f.ConstructorSeasonFactory(),
        f.PointsSystemFactory(),
        f.QualifyingResultFactory(),
    ):
        assert str(obj)

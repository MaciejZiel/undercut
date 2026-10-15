from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.standings import services
from apps.standings.models import ConstructorStanding, DriverStanding

from .factories import (
    ConstructorFactory,
    ConstructorStandingFactory,
    DriverFactory,
    DriverStandingFactory,
    SeasonFactory,
)

pytestmark = pytest.mark.django_db


def test_driver_unique_per_season_round():
    s = DriverStandingFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        DriverStandingFactory(season=s.season, driver=s.driver, after_round=1)
    DriverStandingFactory(season=s.season, driver=s.driver, after_round=2)


def test_constructor_unique_per_season_round():
    s = ConstructorStandingFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        ConstructorStandingFactory(season=s.season, constructor=s.constructor, after_round=1)


def test_negative_points_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        DriverStandingFactory(points=-1)
    with pytest.raises(IntegrityError), transaction.atomic():
        ConstructorStandingFactory(points=-1)


def test_position_nullable_and_half_points_kept():
    row = DriverStandingFactory(position=None, position_text="-", points=Decimal("12.50"))
    row.refresh_from_db()
    assert row.position is None
    assert row.points == Decimal("12.50")


def test_zero_position_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        DriverStandingFactory(position=0)


def test_replace_drivers_creates_updates_deletes_and_is_idempotent():
    season = SeasonFactory()
    a, b, c = DriverFactory(), DriverFactory(), DriverFactory()
    rows = [
        {"driver_id": a.pk, "position": 1, "position_text": "1", "points": "25", "wins": 1},
        {"driver_id": b.pk, "position": 2, "position_text": "2", "points": 18, "podiums": 1},
    ]
    assert services.replace_driver_standings(season.pk, 1, rows) == {
        "created": 2,
        "updated": 0,
        "deleted": 0,
    }
    assert services.replace_driver_standings(season.pk, 1, rows) == {
        "created": 0,
        "updated": 2,
        "deleted": 0,
    }
    new_rows = [
        {"driver_id": b.pk, "position": 1, "position_text": "1", "points": "30.5"},
        {"driver_id": c.pk, "position": 2, "position_text": "2", "points": 12},
    ]
    assert services.replace_driver_standings(season.pk, 1, new_rows) == {
        "created": 1,
        "updated": 1,
        "deleted": 1,
    }
    got = {s.driver_id: s for s in DriverStanding.objects.filter(season=season)}
    assert set(got) == {b.pk, c.pk}
    assert got[b.pk].points == Decimal("30.50")
    assert got[b.pk].wins == 0


def test_replace_does_not_touch_other_rounds_or_seasons():
    season, other = SeasonFactory(), SeasonFactory()
    d = DriverFactory()
    DriverStandingFactory(season=season, after_round=2, driver=d)
    DriverStandingFactory(season=other, after_round=1, driver=d)
    services.replace_driver_standings(season.pk, 1, [])
    assert DriverStanding.objects.count() == 2


def test_replace_constructors_accepts_dataclass_rows():
    season = SeasonFactory()
    t = ConstructorFactory()
    row = services.ConstructorStandingRow(
        constructor_id=t.pk, position=1, position_text="1", points=Decimal("0.5")
    )
    assert services.replace_constructor_standings(season.pk, 3, [row])["created"] == 1
    assert ConstructorStanding.objects.get().points == Decimal("0.50")


def test_replace_rejects_duplicates_and_bad_round_without_changes():
    season = SeasonFactory()
    d = DriverFactory()
    DriverStandingFactory(season=season, driver=d)
    dup = {"driver_id": d.pk, "position": 1, "position_text": "1", "points": 1}
    with pytest.raises(ValueError):
        services.replace_driver_standings(season.pk, 1, [dup, dup])
    with pytest.raises(ValueError):
        services.replace_driver_standings(season.pk, 0, [dup])
    assert DriverStanding.objects.get().points == 25


def test_replace_is_atomic_on_database_error():
    season = SeasonFactory()
    d1, d2 = DriverFactory(), DriverFactory()
    DriverStandingFactory(season=season, driver=d1, points=5)
    rows = [
        {"driver_id": d1.pk, "position": 1, "position_text": "1", "points": 9},
        {"driver_id": d2.pk, "position": 2, "position_text": "2", "points": -1},
    ]
    with pytest.raises(IntegrityError):
        services.replace_driver_standings(season.pk, 1, rows)
    assert DriverStanding.objects.get().points == 5

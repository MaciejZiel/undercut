import pytest

from apps.standings import services

from .factories import DriverFactory, SeasonFactory


@pytest.mark.django_db
def test_replace_reports_unchanged_rows_as_neither_created_nor_updated():
    season = SeasonFactory(year=2024)
    driver = DriverFactory()
    rows = [
        {"driver_id": driver.id, "position": 1, "position_text": "1", "points": "25", "wins": 1}
    ]
    assert services.replace_driver_standings(season.id, 1, rows) == {
        "created": 1,
        "updated": 0,
        "deleted": 0,
    }

    again = services.replace_driver_standings(season.id, 1, rows)

    assert again == {"created": 0, "updated": 0, "deleted": 0}


@pytest.mark.django_db
def test_replace_updates_only_rows_whose_values_changed():
    season = SeasonFactory(year=2024)
    a, b = DriverFactory(), DriverFactory()
    base = [
        {"driver_id": a.id, "position": 1, "position_text": "1", "points": "25"},
        {"driver_id": b.id, "position": 2, "position_text": "2", "points": "18"},
    ]
    services.replace_driver_standings(season.id, 1, base)
    changed = [base[0], {**base[1], "points": "19"}]

    assert services.replace_driver_standings(season.id, 1, changed)["updated"] == 1

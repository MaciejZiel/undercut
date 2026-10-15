import datetime as dt
from decimal import Decimal

import pytest

from apps.catalog import services as s
from apps.catalog.models import Result, Round, Session

pytestmark = pytest.mark.django_db


@pytest.fixture
def base():
    s.upsert_season(s.SeasonData(2024))
    s.upsert_circuit(s.CircuitData("monza", "Monza", locality="Monza", country="Italy"))
    for ref, name in [("verstappen", "Verstappen"), ("norris", "Norris"), ("piastri", "Piastri")]:
        s.upsert_driver(s.DriverData(ref, "Given", name))
    s.upsert_constructor(s.ConstructorData("red_bull", "Red Bull"))


def bundle(rows=(), number=1, kind="RACE"):
    return s.RoundBundle(
        round=s.RoundData(2024, number, "Italian Grand Prix", "monza", dt.date(2024, 9, 1)),
        sessions=[s.SessionBundle(s.SessionData(kind, status="results_final"), results=rows)],
    )


def res(driver, pos, points=0):
    return s.ResultData(
        driver, "red_bull", position=pos, position_text=str(pos), points=Decimal(points)
    )


def test_reference_upserts_are_idempotent():
    first = s.upsert_driver(s.DriverData("alonso", "Fernando", "Alonso", code="ALO"))
    again = s.upsert_driver(s.DriverData("alonso", "Fernando", "Alonso", code="ALO"))
    changed = s.upsert_driver(s.DriverData("alonso", "Fernando", "Alonso", code="ALN"))
    assert first.created and not again.created and not again.updated
    assert changed.updated and changed.id == first.id


def test_slug_collisions_get_a_suffix():
    a = s.upsert_driver(s.DriverData("brown_a", "Alan", "Brown", slug="alan-brown"))
    b = s.upsert_driver(s.DriverData("brown_b", "Alan", "Brown", slug="alan-brown"))
    assert a.id != b.id
    from apps.catalog.models import Driver

    assert Driver.objects.get(pk=b.id).slug == "alan-brown-2"


def test_constructor_season_does_not_overwrite_manual_colour(base):
    s.upsert_constructor_season(s.ConstructorSeasonData("red_bull", 2024, "Red Bull", "#112233"))
    s.upsert_constructor_season(s.ConstructorSeasonData("red_bull", 2024, "RB", "#ffffff"))
    from apps.catalog.models import ConstructorSeason

    cs = ConstructorSeason.objects.get()
    assert (cs.color_hex, cs.display_name) == ("#112233", "Red Bull")


def test_import_round_twice_creates_nothing_new(base):
    rows = [res("verstappen", 1, 25), res("norris", 2, 18)]
    first = s.import_round(bundle(rows))
    second = s.import_round(bundle(rows))
    assert first.results.created == 2 and first.round.created
    assert second.results.created == 0 and second.results.unchanged == 2
    assert not second.round.created and second.sessions.unchanged == 1
    assert Result.objects.count() == 2


def test_manual_override_wins_and_is_reported(base):
    s.import_round(bundle([res("verstappen", 1, 25), res("norris", 2, 18)]))
    locked = Result.objects.get(driver__jolpica_id="verstappen")
    locked.points = 7
    locked.manual_override = True
    locked.save()
    out = s.import_round(bundle([res("verstappen", 1, 25), res("norris", 2, 19)]))
    assert out.results.skipped_manual == 1 and out.results.updated == 1
    locked.refresh_from_db()
    assert locked.points == 7
    assert Result.objects.get(driver__jolpica_id="norris").points == 19


def test_swapped_positions_do_not_trip_the_unique_constraint(base):
    s.import_round(bundle([res("verstappen", 1), res("norris", 2)]))
    out = s.import_round(bundle([res("verstappen", 2), res("norris", 1)]))
    assert out.results.updated == 2
    assert Result.objects.get(driver__jolpica_id="norris").position == 1


def test_incoming_position_held_by_locked_row_is_dropped(base):
    s.import_round(bundle([res("verstappen", 1)]))
    Result.objects.update(manual_override=True)
    out = s.import_round(bundle([res("verstappen", 1), res("norris", 1)]))
    assert out.results.created == 1
    assert Result.objects.get(driver__jolpica_id="norris").position is None


def test_round_is_one_transaction(base):
    bad = bundle([res("verstappen", 1), res("nobody", 2)])
    with pytest.raises(s.MissingReference):
        s.import_round(bad)
    assert Round.objects.count() == 0 and Session.objects.count() == 0


def test_cancelled_round_without_number_is_idempotent(base):
    data = s.RoundData(2024, None, "Cancelled GP", "monza", dt.date(2024, 4, 21), is_cancelled=True)
    a = s.upsert_round(data)
    b = s.upsert_round(data)
    assert a.created and not b.created and a.id == b.id
    assert Round.objects.get(pk=a.id).round is None


def test_session_keeps_known_start_time(base):
    rid = s.upsert_round(s.RoundData(2024, 1, "Italian GP", "monza", dt.date(2024, 9, 1))).id
    start = dt.datetime(2024, 9, 1, 13, tzinfo=dt.UTC)
    s.upsert_session(rid, s.SessionData("RACE", start_utc=start))
    s.upsert_session(rid, s.SessionData("RACE", start_utc=None, status="finished"))
    session = Session.objects.get()
    assert session.start_utc == start and session.status == "finished"


def test_qualifying_upsert(base):
    rid = s.upsert_round(s.RoundData(2024, 1, "Italian GP", "monza", dt.date(2024, 9, 1))).id
    sid = s.upsert_session(rid, s.SessionData("Q")).id
    rows = [s.QualifyingData("norris", "red_bull", 1, 80000, 79000, 78000)]
    assert s.upsert_qualifying(sid, rows).created == 1
    again = s.upsert_qualifying(sid, rows)
    assert again.created == 0 and again.unchanged == 1

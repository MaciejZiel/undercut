import datetime as dt

import pytest

from apps.catalog import scheduling
from apps.catalog import services as catalog
from apps.catalog.models import Result, Session
from apps.events.models import OutboxEvent
from apps.ingestion import handlers
from apps.ingestion.openf1 import matching, practice
from tests.catalog import factories as f

pytestmark = pytest.mark.django_db

NOW = dt.datetime(2026, 10, 9, 14, 0, tzinfo=dt.UTC)
END = dt.datetime(2026, 10, 9, 9, 30, tzinfo=dt.UTC)


@pytest.fixture
def weekend():
    season = f.SeasonFactory(year=2026)
    red_bull = f.ConstructorFactory(name="Red Bull")
    mclaren = f.ConstructorFactory(name="McLaren")
    max_ = f.DriverFactory(code="VER", family_name="Verstappen")
    lando = f.DriverFactory(code="NOR", family_name="Norris")
    earlier = f.RoundFactory(season=season, round=1, date=dt.date(2026, 3, 1))
    race = f.SessionFactory(round=earlier, type=Session.Type.RACE)
    f.ResultFactory(session=race, driver=max_, constructor=red_bull, position=1)
    f.ResultFactory(session=race, driver=lando, constructor=mclaren, position=2)
    rnd = f.RoundFactory(season=season, round=17, date=dt.date(2026, 10, 11))
    fp1 = f.SessionFactory(
        round=rnd,
        type=Session.Type.FP1,
        start_utc=END - dt.timedelta(hours=1),
        end_utc=END,
    )
    return {"round": rnd, "fp1": fp1, "max": max_, "lando": lando, "red_bull": red_bull}


def matched(fp1) -> matching.MatchedSession:
    return matching.MatchedSession(
        session_id=fp1.id,
        session_key=11378,
        type="FP1",
        round_id=fp1.round_id,
        year=2026,
        round_number=fp1.round.round,
        round_name="Singapore",
        status="scheduled",
        start_utc=fp1.start_utc,
        end_utc=fp1.end_utc,
        meeting_key=1296,
    )


class FakeClient:
    def __init__(self, results, drivers):
        self.results, self.drivers, self.calls = results, drivers, []

    def get(self, endpoint, params=None):
        self.calls.append(endpoint)
        return {"session_result": self.results, "drivers": self.drivers}.get(endpoint, [])


RESULTS = [
    {"position": 1, "driver_number": 1, "number_of_laps": 28, "duration": 92.274, "dns": False},
    {"position": 2, "driver_number": 4, "number_of_laps": 26, "duration": 92.472, "dns": False},
    {"position": 3, "driver_number": 99, "number_of_laps": 3, "duration": None, "dns": False},
    {"position": 4, "driver_number": 5, "number_of_laps": 0, "duration": None, "dns": True},
]
DRIVERS = [
    {
        "driver_number": 1,
        "name_acronym": "VER",
        "last_name": "Verstappen",
        "team_name": "Red Bull Racing",
    },
    {"driver_number": 4, "name_acronym": "NOR", "last_name": "Norris", "team_name": "McLaren"},
    {"driver_number": 99, "name_acronym": "ZZZ", "last_name": "Nobody", "team_name": "Unknown"},
]


def test_to_ms_only_accepts_positive_numbers():
    assert practice.to_ms(92.274) == 92274
    assert practice.to_ms(90) == 90000
    for bad in (None, 0, -1, "92.2", True, [1.0]):
        assert practice.to_ms(bad) is None


def test_constructor_comes_from_the_drivers_season_results_then_the_team_name(weekend):
    assert (
        catalog.resolve_constructor_id(weekend["max"].id, 2026, "anything")
        == weekend["red_bull"].id
    )
    rookie = f.DriverFactory(code="NEW")
    assert (
        catalog.resolve_constructor_id(rookie.id, 2026, "Red Bull Racing") == weekend["red_bull"].id
    )
    assert catalog.resolve_constructor_id(rookie.id, 2026, "Mystery Team") is None
    assert catalog.resolve_constructor_id(rookie.id, 2026, "") is None


def test_an_ambiguous_team_name_resolves_to_nothing():
    f.ConstructorFactory(name="Alpine")
    f.ConstructorFactory(name="Alpine F1 Team")
    rookie = f.DriverFactory()
    assert catalog.resolve_constructor_id(rookie.id, 2026, "Alpine F1 Team Racing") is None


def test_import_stores_the_classification_and_finalises_the_session(weekend):
    client = FakeClient(RESULTS, DRIVERS)
    outcome = practice.import_practice_session(client, matched(weekend["fp1"]), now=NOW)
    rows = list(Result.objects.filter(session=weekend["fp1"]).order_by("position"))
    assert [(r.position, r.driver_id, r.best_lap_ms, r.laps) for r in rows] == [
        (1, weekend["max"].id, 92274, 28),
        (2, weekend["lando"].id, 92472, 26),
    ]
    assert rows[0].constructor_id == weekend["red_bull"].id
    assert outcome.rows == 2 and outcome.final is True
    assert any("car 99" in p for p in outcome.problems)  # unknown driver is reported, not guessed
    weekend["fp1"].refresh_from_db()
    assert weekend["fp1"].status == "results_final"
    assert OutboxEvent.objects.filter(type="AnalyticsImported").count() == 1


def test_a_second_run_changes_nothing_and_publishes_nothing(weekend):
    client = FakeClient(RESULTS, DRIVERS)
    practice.import_practice_session(client, matched(weekend["fp1"]), now=NOW)
    events = OutboxEvent.objects.count()
    again = practice.import_practice_session(client, matched(weekend["fp1"]), now=NOW)
    assert again.created == 0 and again.updated == 0
    assert OutboxEvent.objects.count() == events
    assert Result.objects.filter(session=weekend["fp1"]).count() == 2


def test_not_final_while_the_session_is_still_fresh(weekend):
    fresh = END + dt.timedelta(minutes=10)
    outcome = practice.import_practice_session(
        FakeClient(RESULTS, DRIVERS), matched(weekend["fp1"]), now=fresh
    )
    assert outcome.rows == 2 and outcome.final is False
    weekend["fp1"].refresh_from_db()
    assert weekend["fp1"].status != "results_final"


def test_no_published_results_yet_writes_nothing(weekend):
    outcome = practice.import_practice_session(FakeClient([], []), matched(weekend["fp1"]), now=NOW)
    assert outcome.rows == 0
    assert not Result.objects.filter(session=weekend["fp1"]).exists()


def test_a_hand_corrected_row_is_never_overwritten(weekend):
    client = FakeClient(RESULTS, DRIVERS)
    practice.import_practice_session(client, matched(weekend["fp1"]), now=NOW)
    Result.objects.filter(session=weekend["fp1"], position=1).update(
        manual_override=True, best_lap_ms=90000
    )
    practice.import_practice_session(client, matched(weekend["fp1"]), now=NOW)
    assert Result.objects.get(session=weekend["fp1"], position=1).best_lap_ms == 90000


def test_backfill_skips_sessions_that_already_have_results(weekend, monkeypatch):
    monkeypatch.setattr(
        practice.matching,
        "match_year",
        lambda *a, **k: matching.YearMatch(sessions=[matched(weekend["fp1"])]),
    )

    class Year(FakeClient):
        def get(self, endpoint, params=None):
            if endpoint in ("meetings", "sessions"):
                return [{"meeting_key": 1296, "session_key": 11378, "year": 2026}]
            return super().get(endpoint, params)

    client = Year(RESULTS, DRIVERS)
    first = practice.import_practice(client, years=[2026], now=NOW)
    assert len(first) == 1 and first[0].rows == 2
    second = practice.import_practice(client, years=[2026], now=NOW)
    assert second == []  # already has results
    forced = practice.import_practice(client, years=[2026], only_missing=False, now=NOW)
    assert len(forced) == 1


def test_provider_asks_for_recent_unfinished_practice_only(weekend):
    now = END + dt.timedelta(hours=1)
    events = list(handlers.practice_due(now))
    assert [(e.event_type, e.payload["session_id"]) for e in events] == [
        ("PracticeResultsDue", weekend["fp1"].id)
    ]
    assert list(handlers.practice_due(END + dt.timedelta(minutes=5))) == []  # too early
    assert list(handlers.practice_due(END + dt.timedelta(hours=13))) == []  # gave up
    scheduling.set_session_status(weekend["fp1"].id, "results_final")
    assert list(handlers.practice_due(now)) == []


def test_handler_ignores_old_seasons(weekend, monkeypatch):
    season = f.SeasonFactory(year=2019)
    old = f.SessionFactory(round=f.RoundFactory(season=season, round=3), type=Session.Type.FP1)

    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("OpenF1 must not be called for 2019")

    monkeypatch.setattr(handlers, "OpenF1Client", Boom)
    handlers.on_practice_results_due(type("E", (), {"payload": {"session_id": old.id}})())

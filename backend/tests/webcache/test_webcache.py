import datetime as dt

import pytest
from django.test import override_settings

from apps.catalog.models import Season
from apps.events import registry
from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.worker import process_batch
from apps.webcache import client, handlers, tags
from tests.catalog.factories import RoundFactory, SeasonFactory, SessionFactory

pytestmark = pytest.mark.django_db

CONFIGURED = {
    "REVALIDATE_URL": "http://frontend/_internal/revalidate",
    "REVALIDATE_SECRET": "s3cret",
}


class Recorder:
    def __init__(self, status=200):
        self.status = status
        self.calls = []

    def __call__(self, url, secret, tags_):
        self.calls.append((url, secret, tags_))
        return self.status


@pytest.fixture
def race():
    season = SeasonFactory(year=2024)
    round_ = RoundFactory(season=season, round=5)
    return SessionFactory(round=round_, type="RACE")


@pytest.fixture
def wired(monkeypatch):
    registry.clear()
    handlers.register()
    recorder = Recorder()
    monkeypatch.setattr(client, "_post", recorder)
    yield recorder
    registry.clear()


# --------------------------------------------------------------------------- client


@override_settings(**CONFIGURED)
def test_sends_unique_sorted_tags_with_the_secret():
    recorder = Recorder()
    sent = client.revalidate(["b", "a", "a"], post=recorder)
    assert sent == 2
    assert recorder.calls == [("http://frontend/_internal/revalidate", "s3cret", ["a", "b"])]


@override_settings(**CONFIGURED)
def test_splits_requests_at_the_frontend_limit():
    recorder = Recorder()
    client.revalidate([f"season:{y}" for y in range(250)], post=recorder)
    assert [len(c[2]) for c in recorder.calls] == [100, 100, 50]


@override_settings(REVALIDATE_URL="http://x", REVALIDATE_SECRET="")
def test_does_nothing_without_a_secret():
    recorder = Recorder()
    assert client.revalidate(["drivers"], post=recorder) == 0
    assert recorder.calls == []


@override_settings(**CONFIGURED)
def test_a_refusal_raises_so_the_outbox_retries():
    with pytest.raises(client.RevalidateError, match="401"):
        client.revalidate(["drivers"], post=Recorder(status=401))


@override_settings(**CONFIGURED)
def test_no_tags_means_no_request():
    recorder = Recorder()
    assert client.revalidate([], post=recorder) == 0 and recorder.calls == []


def test_tags_match_the_frontend_grammar():
    import re

    grammar = re.compile(r"^[a-z][a-z-]*(:[A-Za-z0-9._-]{1,200})?$")
    for tag in {tags.season(2024), tags.round_(2024, 5), "drivers", "standings"}:
        assert grammar.match(tag)


# --------------------------------------------------------------------------- tags


def test_results_purge_the_round_season_and_statistics(race):
    assert tags.for_session(race.id, results_changed=True) == {
        "season:2024",
        "round:2024-5",
        "drivers",
        "constructors",
        "circuits",
        "seasons",
    }


def test_analytics_only_purge_the_round(race):
    assert tags.for_session(race.id, results_changed=False) == {"season:2024", "round:2024-5"}


def test_unknown_session_gives_no_tags():
    assert tags.for_session(999999, results_changed=True) == set()


def test_standings_purge_titles_too():
    assert {"standings", "season:2024", "drivers", "constructors", "seasons"} == tags.for_standings(
        2024
    )


def test_history_import_covers_the_imported_years():
    for year in (2022, 2023, 2024):
        SeasonFactory(year=year)
    result = tags.for_history_import(2023, 2024)
    assert {"season:2023", "season:2024", "search"} <= result
    assert "season:2022" not in result
    assert Season.objects.count() == 3


# --------------------------------------------------------------------------- through the worker


@override_settings(**CONFIGURED)
def test_a_results_event_reaches_the_frontend(race, wired):
    publish("SessionResultsFinalized", key=f"session:{race.id}", payload={"session_id": race.id})

    process_batch()

    [(url, secret, sent)] = wired.calls
    assert (url, secret) == (CONFIGURED["REVALIDATE_URL"], "s3cret")
    assert "round:2024-5" in sent
    assert OutboxEvent.objects.get().status == "done"


@override_settings(**CONFIGURED)
def test_an_unreachable_frontend_is_retried_later(race, monkeypatch):
    registry.clear()
    handlers.register()

    def down(*_args):
        raise client.RevalidateError("down")

    monkeypatch.setattr(client, "_post", down)
    event = publish("SessionResultsFinalized", key="session:1", payload={"session_id": race.id})

    process_batch()

    event.refresh_from_db()
    assert event.status == "pending" and event.attempts == 1
    assert event.available_at > dt.datetime.now(dt.UTC)
    registry.clear()

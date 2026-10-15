import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.models import Circuit, Round, Season, Session
from apps.events.models import OutboxEvent
from apps.ingestion import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def weekend():
    season = Season.objects.create(year=2025)
    circuit = Circuit.objects.create(slug="monza", name="Monza")
    rnd = Round.objects.create(
        season=season, round=16, name="Italian Grand Prix", circuit=circuit, date="2025-09-07"
    )
    start = dt.datetime(2025, 9, 7, 13, tzinfo=dt.UTC)
    for kind in (Session.Type.Q, Session.Type.RACE):
        Session.objects.create(
            round=rnd, type=kind, start_utc=start, end_utc=start + dt.timedelta(hours=2)
        )
    return rnd


def events():
    return list(OutboxEvent.objects.order_by("id").values_list("type", "key"))


def test_queues_results_for_every_session_and_analytics_for_the_race(weekend):
    queued = services.request_round_resync(2025, 16)
    assert queued == {"SessionResultsDue": 2, "AnalyticsDue": 1, "PracticeResultsDue": 0}
    kinds = [t for t, _ in events()]
    assert kinds.count("SessionResultsDue") == 2 and kinds.count("AnalyticsDue") == 1
    race = Session.objects.get(round=weekend, type=Session.Type.RACE)
    assert ("AnalyticsDue", f"session:{race.id}") in events()


def test_analytics_can_be_skipped_and_old_seasons_have_none(weekend):
    assert services.request_round_resync(2025, 16, analytics=False)["AnalyticsDue"] == 0
    season = Season.objects.create(year=2019)
    old = Round.objects.create(
        season=season, round=1, name="Old GP", circuit=weekend.circuit, date="2019-03-17"
    )
    Session.objects.create(
        round=old, type=Session.Type.RACE, start_utc=dt.datetime(2019, 3, 17, tzinfo=dt.UTC)
    )
    assert services.request_round_resync(2019, 1)["AnalyticsDue"] == 0


def test_unknown_round_queues_nothing(weekend):
    with pytest.raises(services.RoundNotFound):
        services.request_round_resync(2025, 99)
    assert not OutboxEvent.objects.exists()


def test_management_command_reports_what_it_queued(weekend):
    out = StringIO()
    call_command("resync_round", "2025", "16", stdout=out)
    assert (
        "Queued 2 results sync(s), 0 practice import(s) and 1 analytics import(s)" in out.getvalue()
    )
    with pytest.raises(CommandError, match="No round 99"):
        call_command("resync_round", "2025", "99")


def test_admin_page_queues_the_round(weekend, client, django_user_model):
    admin = django_user_model.objects.create_superuser("root", "root@example.com", "pw-pw-pw-pw-1")
    client.force_login(admin)
    assert client.get("/admin/ingestion/syncrun/").status_code == 200
    page = client.get("/admin/ingestion/syncrun/resync/")
    assert page.status_code == 200 and b"Queue the sync" in page.content
    res = client.post(
        "/admin/ingestion/syncrun/resync/", {"year": 2025, "round": 16, "analytics": "on"}
    )
    assert res.status_code == 302
    assert len(events()) == 3
    bad = client.post("/admin/ingestion/syncrun/resync/", {"year": 2025, "round": 30})
    assert bad.status_code == 200 and b"No round 30" in bad.content


def test_admin_page_needs_a_staff_login(weekend, client):
    res = client.get("/admin/ingestion/syncrun/resync/")
    assert res.status_code == 302 and "login" in res["Location"]


def test_practice_sessions_are_queued_for_the_practice_import(weekend):
    start = dt.datetime(2025, 9, 5, 11, tzinfo=dt.UTC)
    Session.objects.create(round=weekend, type=Session.Type.FP1, start_utc=start)
    queued = services.request_round_resync(2025, 16)
    assert queued["PracticeResultsDue"] == 1
    assert queued["SessionResultsDue"] == 2
    fp = Session.objects.get(round=weekend, type=Session.Type.FP1)
    assert ("PracticeResultsDue", f"session:{fp.id}") in events()

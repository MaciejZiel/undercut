import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command

from apps.events.models import OutboxEvent

pytestmark = pytest.mark.django_db


def run(*args):
    out = StringIO()
    code = 0
    try:
        call_command("check_pipeline", *args, stdout=out)
    except SystemExit as exc:
        code = exc.code
    return code, out.getvalue()


def test_exit_zero_when_healthy(healthy_heartbeats):
    assert run() == (0, "OK\n")


def test_exit_one_with_dead_event(healthy_heartbeats, make_event):
    make_event(status=OutboxEvent.Status.DEAD)
    code, out = run()
    assert code == 1
    assert "outbox_dead" in out


def test_exit_one_on_stuck_outbox(healthy_heartbeats, make_event):
    make_event(age=timedelta(minutes=45))
    assert run()[0] == 1


def test_exit_one_when_nothing_reported():
    code, out = run()
    assert code == 1
    assert "heartbeat_missing" in out


def test_exit_one_on_missing_results(healthy_heartbeats, make_race):
    make_race(ended_ago=timedelta(hours=30))
    code, out = run()
    assert code == 1
    assert "results_missing" in out


def test_json_output(healthy_heartbeats, make_event):
    make_event(status=OutboxEvent.Status.DEAD)
    code, out = run("--json")
    body = json.loads(out)
    assert code == 1
    assert body["ok"] is False
    assert body["problems"][0]["code"] == "outbox_dead"


def test_exit_one_when_a_sync_job_keeps_failing(healthy_heartbeats):
    from django.utils import timezone

    from apps.ingestion.models import SyncRun

    for minutes in (30, 5):
        started = timezone.now() - timedelta(minutes=minutes)
        SyncRun.objects.create(
            source="jolpica-api",
            job="standings",
            status=SyncRun.Status.FAILED,
            started_at=started,
            finished_at=started,
        )
    code, out = run()
    assert code == 1
    assert "sync_failing" in out and "jolpica-api/standings" in out

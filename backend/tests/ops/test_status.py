from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import Session
from apps.events.models import OutboxEvent
from apps.ingestion.models import SyncRun
from apps.ops import status
from apps.ops.models import Heartbeat

pytestmark = pytest.mark.django_db


def codes(problems):
    return {p.code for p in problems}


def test_outbox_stats_counts_and_oldest_age(make_event):
    make_event(age=timedelta(minutes=10))
    make_event(age=timedelta(minutes=2))
    make_event(status=OutboxEvent.Status.DEAD)
    make_event(status=OutboxEvent.Status.DONE)
    stats = status.outbox_stats()
    assert stats["pending"] == 2
    assert stats["dead"] == 1
    assert 590 <= stats["oldest_pending_age_seconds"] <= 620


def test_outbox_stats_empty():
    stats = status.outbox_stats()
    assert stats["pending"] == 0
    assert stats["oldest_pending_age_seconds"] is None


def test_healthy_pipeline_has_no_problems(healthy_heartbeats, make_event):
    make_event(age=timedelta(minutes=5))
    assert status.pipeline_problems() == []


def test_dead_event_is_a_problem(healthy_heartbeats, make_event):
    make_event(status=OutboxEvent.Status.DEAD)
    assert codes(status.pipeline_problems()) == {"outbox_dead"}


def test_pending_event_older_than_30_minutes_is_a_problem(healthy_heartbeats, make_event):
    make_event(age=timedelta(minutes=31))
    assert codes(status.pipeline_problems()) == {"outbox_stuck"}


def test_pending_event_just_under_30_minutes_is_fine(healthy_heartbeats, make_event):
    make_event(age=timedelta(minutes=29))
    assert status.pipeline_problems() == []


def test_missing_heartbeats_are_problems():
    assert codes(status.pipeline_problems()) == {"heartbeat_missing"}


def test_stale_heartbeat_is_a_problem(healthy_heartbeats):
    Heartbeat.objects.filter(name="scheduler").update(beat_at=timezone.now() - timedelta(minutes=6))
    problems = status.pipeline_problems()
    assert codes(problems) == {"heartbeat_stale"}
    assert "scheduler" in problems[0].message


def test_heartbeat_just_under_5_minutes_is_fine(healthy_heartbeats):
    Heartbeat.objects.update(beat_at=timezone.now() - timedelta(minutes=4))
    assert status.pipeline_problems() == []


def test_race_without_final_results_after_24h_is_a_problem(healthy_heartbeats, make_race):
    make_race(ended_ago=timedelta(hours=25))
    assert codes(status.pipeline_problems()) == {"results_missing"}


def test_race_without_final_results_within_24h_is_fine(healthy_heartbeats, make_race):
    make_race(ended_ago=timedelta(hours=23))
    assert status.pipeline_problems() == []


def test_final_results_are_fine(healthy_heartbeats, make_race):
    make_race(ended_ago=timedelta(days=3), status=Session.Status.RESULTS_FINAL)
    assert status.pipeline_problems() == []


def test_only_the_latest_ended_race_counts(healthy_heartbeats, make_race):
    make_race(ended_ago=timedelta(days=30))  # old, never finalized: superseded by the newer race
    make_race(ended_ago=timedelta(days=2), status=Session.Status.RESULTS_FINAL)
    assert status.pipeline_problems() == []


def test_future_and_cancelled_races_are_ignored(healthy_heartbeats, make_race):
    future = make_race(ended_ago=timedelta(hours=-5))
    cancelled = make_race(ended_ago=timedelta(days=5))
    cancelled.round.is_cancelled = True
    cancelled.round.save()
    assert future and status.pipeline_problems() == []


def test_race_without_end_time_uses_start_plus_three_hours(healthy_heartbeats, make_race):
    make_race(ended_ago=timedelta(hours=40), end_known=False)
    # start is end-2h = 42 h ago; assumed end = 39 h ago
    race = status.data_freshness()["latest_race"]
    assert 38 * 3600 < race["ended_age_seconds"] < 40 * 3600
    assert codes(status.pipeline_problems()) == {"results_missing"}


def test_freshness_reports_finalization_time(make_race, make_event):
    race = make_race(ended_ago=timedelta(days=1), status=Session.Status.RESULTS_FINAL)
    make_event(
        status=OutboxEvent.Status.DONE,
        type="SessionResultsFinalized",
        key=f"session:{race.pk}",
        age=timedelta(hours=20),
    )
    latest = status.data_freshness()["latest_race"]
    assert latest["results_final"] is True
    assert latest["finalized_at"] is not None


def test_freshness_without_races():
    assert status.data_freshness() == {"latest_race": None}


def test_last_sync_run_per_source_and_job():
    SyncRun.objects.create(source="jolpica-api", job="results", status="failed")
    newest = SyncRun.objects.create(
        source="jolpica-api", job="results", status="success", finished_at=timezone.now()
    )
    SyncRun.objects.create(source="openf1", job="laps", status="running")
    runs = status.last_sync_runs()
    assert len(runs) == 2
    by_key = {(r["source"], r["job"]): r for r in runs}
    assert by_key[("jolpica-api", "results")]["status"] == "success"
    assert newest.finished_at is not None


def test_table_sizes_lists_largest_first():
    tables = status.table_sizes(limit=5)
    assert 0 < len(tables) <= 5
    sizes = [t["total_bytes"] for t in tables]
    assert sizes == sorted(sizes, reverse=True)

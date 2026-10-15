"""Read-only pipeline state: used by /api/ready/, the staff status endpoint and check_pipeline."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import connection
from django.db.models import F, Min
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalog.models import Result, Session
from apps.events.models import OutboxEvent
from apps.ingestion.failures import failing_jobs
from apps.ingestion.models import SyncRun

from .heartbeat import EXPECTED
from .models import Heartbeat

# Alarm thresholds (check_pipeline and /api/ready/).
OUTBOX_MAX_PENDING_AGE = timedelta(minutes=30)
HEARTBEAT_MAX_AGE = timedelta(minutes=5)
RESULTS_GRACE = timedelta(hours=24)
# Race sessions without an end time are assumed to last this long.
ASSUMED_RACE_DURATION = timedelta(hours=3)
FINALIZED_EVENT = "SessionResultsFinalized"


def _seconds(delta: timedelta | None) -> int | None:
    return None if delta is None else int(delta.total_seconds())


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def outbox_stats(now: datetime | None = None) -> dict:
    now = now or timezone.now()
    pending = OutboxEvent.objects.filter(status=OutboxEvent.Status.PENDING)
    oldest = pending.aggregate(oldest=Min("created_at"))["oldest"]
    return {
        "pending": pending.count(),
        "dead": OutboxEvent.objects.filter(status=OutboxEvent.Status.DEAD).count(),
        "oldest_pending_at": _iso(oldest),
        "oldest_pending_age_seconds": _seconds(now - oldest) if oldest else None,
    }


def last_sync_runs(now: datetime | None = None) -> list[dict]:
    """The latest SyncRun of every (source, job) pair."""
    now = now or timezone.now()
    runs = SyncRun.objects.order_by("source", "job", "-started_at", "-id").distinct("source", "job")
    out = []
    for run in runs:
        reference = run.finished_at or run.started_at
        out.append(
            {
                "source": run.source,
                "job": run.job,
                "status": run.status,
                "started_at": _iso(run.started_at),
                "finished_at": _iso(run.finished_at),
                "age_seconds": _seconds(now - reference),
                "created": run.created,
                "updated": run.updated,
                "skipped": run.skipped,
                "error_count": len(run.errors or []),
            }
        )
    return out


def heartbeats(now: datetime | None = None) -> list[dict]:
    """Expected processes first; a process that never reported has `beat_at: null`."""
    now = now or timezone.now()
    seen = {hb.name: hb for hb in Heartbeat.objects.all()}
    names = [*EXPECTED, *sorted(set(seen) - set(EXPECTED))]
    out = []
    for name in names:
        hb = seen.get(name)
        out.append(
            {
                "name": name,
                "beat_at": _iso(hb.beat_at) if hb else None,
                "age_seconds": _seconds(now - hb.beat_at) if hb else None,
            }
        )
    return out


def data_freshness(now: datetime | None = None) -> dict:
    """The latest race that has ended and whether its results are final."""
    now = now or timezone.now()
    ended_at = Coalesce("end_utc", F("start_utc") + ASSUMED_RACE_DURATION)
    race = (
        Session.objects.filter(type=Session.Type.RACE, round__is_cancelled=False)
        .annotate(ended_at=ended_at)
        .filter(ended_at__lte=now)
        .select_related("round", "round__season")
        .order_by("-ended_at", "-id")
        .first()
    )
    if race is None:
        return {"latest_race": None}
    final = race.status == Session.Status.RESULTS_FINAL
    finalized_at = (
        OutboxEvent.objects.filter(type=FINALIZED_EVENT, key=f"session:{race.pk}").aggregate(
            first=Min("created_at")
        )["first"]
        if final
        else None
    )
    return {
        "latest_race": {
            "session_id": race.pk,
            "season": race.round.season.year,
            "round": race.round.round,
            "name": race.round.name,
            "ended_at": _iso(race.ended_at),  # pyright: ignore[reportAttributeAccessIssue]
            "ended_age_seconds": _seconds(now - race.ended_at),  # pyright: ignore[reportAttributeAccessIssue]
            "status": race.status,
            "results_final": final,
            # The first finalization event is the best record of when results became final.
            "finalized_at": _iso(finalized_at),
            "result_rows": Result.objects.filter(session=race).count(),
        }
    }


def table_sizes(limit: int = 10) -> list[dict]:
    """Largest tables of the current schema (total size including indexes)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname, pg_total_relation_size(c.oid), c.reltuples::bigint
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname = current_schema()
            ORDER BY 2 DESC, 1
            LIMIT %s
            """,
            [limit],
        )
        return [
            {"table": name, "total_bytes": size, "estimated_rows": max(rows, 0)}
            for name, size, rows in cursor.fetchall()
        ]


def full_status(now: datetime | None = None) -> dict:
    now = now or timezone.now()
    return {
        "generated_at": now.isoformat(),
        "outbox": outbox_stats(now),
        "sync_runs": last_sync_runs(now),
        "heartbeats": heartbeats(now),
        "freshness": data_freshness(now),
        "tables": table_sizes(),
    }


@dataclass(frozen=True)
class Problem:
    code: str
    message: str


def outbox_problems(now: datetime | None = None) -> list[Problem]:
    stats = outbox_stats(now)
    problems = []
    if stats["dead"]:
        problems.append(Problem("outbox_dead", f"{stats['dead']} dead outbox event(s)"))
    age = stats["oldest_pending_age_seconds"]
    if age is not None and age > OUTBOX_MAX_PENDING_AGE.total_seconds():
        problems.append(
            Problem("outbox_stuck", f"oldest pending outbox event is {age // 60} min old")
        )
    return problems


def pipeline_problems(now: datetime | None = None) -> list[Problem]:
    """Everything check_pipeline alarms on. Empty list means healthy."""
    now = now or timezone.now()
    problems = outbox_problems(now)
    for hb in heartbeats(now):
        age = hb["age_seconds"]
        if age is None:
            problems.append(Problem("heartbeat_missing", f"{hb['name']} has never reported"))
        elif age > HEARTBEAT_MAX_AGE.total_seconds():
            problems.append(
                Problem("heartbeat_stale", f"{hb['name']} last reported {age // 60} min ago")
            )
    for source, job, failures in failing_jobs(now):
        problems.append(Problem("sync_failing", f"{source}/{job} failed {failures} times in a row"))
    race = data_freshness(now)["latest_race"]
    if race and not race["results_final"]:
        if race["ended_age_seconds"] > RESULTS_GRACE.total_seconds():
            hours = race["ended_age_seconds"] // 3600
            problems.append(
                Problem(
                    "results_missing",
                    f"{race['season']} {race['name']} ended {hours} h ago without final results",
                )
            )
    return problems

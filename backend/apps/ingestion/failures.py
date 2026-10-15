"""Repeated failures of a sync job: counted here, reported by alerts.py and check_pipeline."""

import datetime as dt

from django.utils import timezone

from .models import SyncRun

# A job counts as failing after this many failed runs in a row.
FAILING_AFTER = 2
# Only jobs that failed recently are reported: an old failure of a job that is no longer
# scheduled must not raise the alarm forever.
RECENT = dt.timedelta(hours=24)
_LOOKBACK = 50


def consecutive_failures(source: str, job: str) -> int:
    """Failed runs of (source, job) since its last run that did not fail (running ones skipped)."""
    runs = (
        SyncRun.objects.filter(source=source, job=job)
        .exclude(status=SyncRun.Status.RUNNING)
        .order_by("-started_at", "-id")
        .values_list("status", flat=True)[:_LOOKBACK]
    )
    count = 0
    for status in runs:
        if status != SyncRun.Status.FAILED:
            break
        count += 1
    return count


def failing_jobs(now: dt.datetime | None = None) -> list[tuple[str, str, int]]:
    """(source, job, consecutive failures) for jobs whose latest run failed recently."""
    now = now or timezone.now()
    latest = (
        SyncRun.objects.exclude(status=SyncRun.Status.RUNNING)
        .order_by("source", "job", "-started_at", "-id")
        .distinct("source", "job")
    )
    out = []
    for run in latest:
        if (
            run.status != SyncRun.Status.FAILED
            or now - (run.finished_at or run.started_at) > RECENT
        ):
            continue
        count = consecutive_failures(run.source, run.job)
        if count >= FAILING_AFTER:
            out.append((run.source, run.job, count))
    return out

"""Recurring jobs. The scheduler only publishes events; handlers do the actual work."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ScheduleSlot
from .publisher import publish


@dataclass(frozen=True)
class Recurring:
    """Fires at HH:MM UTC every day, or only on `weekday` (Monday=0) when given."""

    name: str
    event_type: str
    hour: int
    minute: int = 0
    weekday: int | None = None

    def latest_slot(self, now: datetime) -> datetime:
        """Most recent scheduled time that is <= now."""
        candidate = now.astimezone(UTC).replace(
            hour=self.hour, minute=self.minute, second=0, microsecond=0
        )
        if candidate > now:
            candidate -= timedelta(days=1)
        if self.weekday is not None:
            candidate -= timedelta(days=(candidate.weekday() - self.weekday) % 7)
        return candidate


# Event-driven versions of the schedule from the spec. Session-relative jobs
# (results after end_utc, prediction lock at qualifying start) arrive with the catalog.
SCHEDULE: list[Recurring] = [
    Recurring("calendar-sync", "CalendarSyncDue", hour=5),
    Recurring("results-corrections", "ResultsCorrectionsDue", hour=6, weekday=0),
    Recurring("demo-reset", "DemoResetDue", hour=3),
]


def run_due(now: datetime | None = None, schedule: list[Recurring] | None = None) -> int:
    """Publish an event for every job whose latest slot has not fired yet."""
    now = now or timezone.now()
    fired = 0
    for job in SCHEDULE if schedule is None else schedule:
        slot = job.latest_slot(now)
        try:
            with transaction.atomic():
                ScheduleSlot.objects.create(job=job.name, slot=slot)
                publish(job.event_type, key=f"{job.name}", payload={"slot": slot.isoformat()})
        except IntegrityError:
            continue  # already fired for this slot
        fired += 1
    return fired

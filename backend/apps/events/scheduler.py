"""Recurring jobs. The scheduler only publishes events; handlers do the actual work."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class DueEvent:
    """An occurrence a provider wants fired. (job, slot) is the dedupe key."""

    job: str
    slot: datetime
    event_type: str
    key: str = ""
    payload: dict = field(default_factory=dict)


Provider = Callable[[datetime], Iterable[DueEvent]]
_providers: list[Provider] = []


def register_provider(provider: Provider) -> Provider:
    """Let a module schedule data-dependent jobs (e.g. "results due after a session ends").

    Providers must be cheap and pure: they only decide what is due, handlers do the work.
    """
    if provider not in _providers:
        _providers.append(provider)
    return provider


def clear_providers() -> None:
    """For tests."""
    _providers.clear()


def _fire(due: DueEvent) -> bool:
    try:
        with transaction.atomic():
            ScheduleSlot.objects.create(job=due.job, slot=due.slot)
            publish(due.event_type, key=due.key, payload=due.payload)
    except IntegrityError:
        return False  # already fired for this slot
    return True


def run_due(
    now: datetime | None = None,
    schedule: list[Recurring] | None = None,
    providers: list[Provider] | None = None,
) -> int:
    """Publish an event for every job whose latest slot has not fired yet."""
    now = now or timezone.now()
    fired = 0
    for job in SCHEDULE if schedule is None else schedule:
        slot = job.latest_slot(now)
        fired += _fire(
            DueEvent(
                job.name, slot, job.event_type, key=job.name, payload={"slot": slot.isoformat()}
            )
        )
    for provider in _providers if providers is None else providers:
        fired += sum(_fire(due) for due in provider(now))
    return fired

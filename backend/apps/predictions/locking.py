"""The server-side lock of predictions (FR-602): qualifying start, compared in UTC."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from apps.catalog import selectors as catalog

from . import errors


def now() -> datetime:
    """The only clock the game reads (UTC, server side). Tests replace this function."""
    return timezone.now()


def closes_at(round_id: int) -> datetime | None:
    """Start of the qualifying session, None when unknown.

    Read on every call, so a changed qualifying time moves the lock automatically.
    """
    return catalog.qualifying_start(round_id)


def is_locked(round_id: int) -> bool:
    """True from the qualifying start on (inclusive). An unknown time counts as not locked;
    submitting still fails with QualifyingTimeUnknown."""
    start = closes_at(round_id)
    return start is not None and now() >= start


def assert_picks_visible(round_id: int) -> None:
    if not is_locked(round_id):
        raise errors.PicksHidden()

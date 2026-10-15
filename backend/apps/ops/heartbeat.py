"""Heartbeats written by the long-running management commands."""

import logging
import time

from django.utils import timezone

from .models import Heartbeat

logger = logging.getLogger(__name__)

SCHEDULER = "scheduler"
OUTBOX_WORKER = "outbox-worker"
EXPECTED = (SCHEDULER, OUTBOX_WORKER)

# A worker loop spins every second when busy; one write per 30 s is plenty for a 5 minute alarm.
MIN_INTERVAL_SECONDS = 30.0
_last_write: dict[str, float] = {}


def beat(name: str, *, force: bool = False) -> bool:
    """Record that `name` is alive. Cheap to call on every loop turn, never raises.

    Returns True when a row was written. A failing database must not stop the worker: the
    stale heartbeat is itself the alert.
    """
    now = time.monotonic()
    last = _last_write.get(name)
    if not force and last is not None and now - last < MIN_INTERVAL_SECONDS:
        return False
    try:
        Heartbeat.objects.update_or_create(name=name, defaults={"beat_at": timezone.now()})
    except Exception:
        logger.warning("Could not record heartbeat %s", name, exc_info=True)
        return False
    _last_write[name] = now
    return True

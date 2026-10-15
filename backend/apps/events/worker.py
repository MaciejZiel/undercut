import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import registry
from .models import OutboxEvent

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
BASE_BACKOFF_SECONDS = 5


def backoff(attempts: int) -> timedelta:
    return timedelta(seconds=BASE_BACKOFF_SECONDS * 2 ** (attempts - 1))


def process_batch(limit: int = 20) -> int:
    """Deliver due events once. Returns the number of events taken from the outbox.

    Rows are claimed with SELECT ... FOR UPDATE SKIP LOCKED, so several workers can run
    side by side without handling the same event twice at the same moment.
    """
    handled = 0
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(status=OutboxEvent.Status.PENDING, available_at__lte=timezone.now())
            .order_by("id")[:limit]
        )
        blocked_keys: set[str] = set()
        for event in events:
            # Keep per-key order: if an earlier event of this key failed, wait for it.
            if event.key and event.key in blocked_keys:
                continue
            handled += 1
            if not _deliver(event) and event.key:
                blocked_keys.add(event.key)
    return handled


def _deliver(event: OutboxEvent) -> bool:
    try:
        # Savepoint: a failing handler must not poison the claiming transaction.
        with transaction.atomic():
            for handler in registry.handlers_for(event.type):
                handler(event)
    except Exception as exc:
        event.attempts += 1
        event.last_error = f"{type(exc).__name__}: {exc}"
        if event.attempts >= MAX_ATTEMPTS:
            event.status = OutboxEvent.Status.DEAD
        else:
            event.available_at = timezone.now() + backoff(event.attempts)
        event.save(update_fields=["attempts", "last_error", "status", "available_at"])
        logger.exception("Event %s failed (attempt %s)", event, event.attempts)
        return False
    event.status = OutboxEvent.Status.DONE
    event.processed_at = timezone.now()
    event.save(update_fields=["status", "processed_at"])
    return True

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


def _handler_ids(event_type: str) -> list[tuple[str, registry.Handler]]:
    """Stable ids for the handlers of an event type (a repeated name gets a #n suffix)."""
    seen: dict[str, int] = {}
    out = []
    for handler in registry.handlers_for(event_type):
        base = f"{handler.__module__}.{handler.__qualname__}"
        seen[base] = seen.get(base, 0) + 1
        out.append((base if seen[base] == 1 else f"{base}#{seen[base]}", handler))
    return out


def _deliver(event: OutboxEvent) -> bool:
    """Run every handler that has not succeeded yet. One failing handler never re-runs the
    others, and never stops them: they are independent consumers of the same fact."""
    delivered = list(event.delivered)
    errors: list[str] = []
    for handler_id, handler in _handler_ids(event.type):
        if handler_id in delivered:
            continue
        try:
            # Savepoint: a failing handler must not poison the claiming transaction.
            with transaction.atomic():
                handler(event)
        except Exception as exc:
            errors.append(f"{handler_id}: {type(exc).__name__}: {exc}")
            logger.exception("Handler %s failed for %s", handler_id, event)
        else:
            delivered.append(handler_id)
    event.delivered = delivered
    if errors:
        event.attempts += 1
        event.last_error = "; ".join(errors)
        if event.attempts >= MAX_ATTEMPTS:
            event.status = OutboxEvent.Status.DEAD
        else:
            event.available_at = timezone.now() + backoff(event.attempts)
        event.save(update_fields=["attempts", "last_error", "status", "available_at", "delivered"])
        return False
    event.status = OutboxEvent.Status.DONE
    event.processed_at = timezone.now()
    event.save(update_fields=["status", "processed_at", "delivered"])
    return True

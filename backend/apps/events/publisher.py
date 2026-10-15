from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .models import OutboxEvent


def publish(
    event_type: str,
    *,
    key: str = "",
    payload: dict | None = None,
    available_at: datetime | None = None,
) -> OutboxEvent:
    """Record an event inside the caller's transaction, so data and event commit together."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("publish() must be called inside transaction.atomic()")
    return OutboxEvent.objects.create(
        type=event_type,
        key=key,
        payload=payload or {},
        available_at=available_at or timezone.now(),
    )

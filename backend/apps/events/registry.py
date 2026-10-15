"""Handler registry: modules subscribe to event types without importing each other."""

from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import OutboxEvent

Handler = Callable[["OutboxEvent"], None]

_handlers: dict[str, list[Handler]] = defaultdict(list)


def subscribe(event_type: str) -> Callable[[Handler], Handler]:
    """Register a handler. Handlers are delivered at-least-once, so they MUST be idempotent."""

    def decorator(func: Handler) -> Handler:
        if func not in _handlers[event_type]:
            _handlers[event_type].append(func)
        return func

    return decorator


def handlers_for(event_type: str) -> list[Handler]:
    return list(_handlers.get(event_type, []))


def clear() -> None:
    """For tests."""
    _handlers.clear()

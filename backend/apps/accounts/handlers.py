import logging

from apps.events.registry import subscribe

from . import services

logger = logging.getLogger(__name__)


def handle_demo_reset_due(event) -> None:
    """Nightly reset of the demo account. Idempotent: it always restores the same state."""
    services.reset_demo_account()


def register_handlers() -> None:
    subscribe("DemoResetDue")(handle_demo_reset_due)

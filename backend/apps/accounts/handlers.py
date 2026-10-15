import logging

from apps.events.registry import subscribe

from . import demo

logger = logging.getLogger(__name__)


def handle_demo_reset_due(event) -> None:
    """Nightly reset of the demo account. Idempotent: it always restores the same state."""
    demo.reset_demo_data()


def register_handlers() -> None:
    subscribe("DemoResetDue")(handle_demo_reset_due)

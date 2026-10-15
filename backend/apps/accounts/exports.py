"""Registry of personal-data export providers (FR-506, NFR-303).

Other modules register a function that returns the user's data they own, so accounts never
imports their models. ``register_export_provider`` is meant to be called from ``AppConfig.ready``.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

ExportProvider = Callable[[Any], Any]

_providers: dict[str, ExportProvider] = {}


def register_export_provider(name: str, func: ExportProvider) -> None:
    """Register ``func(user) -> JSON-serialisable`` under ``name``.

    Registering the same name again replaces the provider (idempotent across repeated ready()
    calls and reloads). The name becomes a top-level key of the export document.
    """
    if not name or not callable(func):
        raise ValueError("an export provider needs a name and a callable")
    if name in RESERVED_NAMES:
        raise ValueError(f"{name!r} is reserved for the account's own data")
    _providers[name] = func


def unregister_export_provider(name: str) -> None:
    """For tests."""
    _providers.pop(name, None)


def provider_names() -> list[str]:
    return sorted(_providers)


def collect(user) -> dict[str, Any]:
    """Run every provider for ``user``.

    A failing provider fails the whole export: a silently incomplete copy of someone's data
    would be worse than an error they can retry.
    """
    return {name: _providers[name](user) for name in sorted(_providers)}


RESERVED_NAMES = frozenset({"profile", "favorites", "exported_at"})

"""Optional Sentry error reporting. The app runs unchanged when `sentry-sdk` is not installed."""

import logging
from typing import Any

from .redaction import redact

logger = logging.getLogger(__name__)

_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-csrftoken", "x-forwarded-for"}


def _scrub_text(value: Any) -> Any:
    return redact(value) if isinstance(value, str) else value


def scrub_event(event: dict, hint: dict | None = None) -> dict | None:
    """`before_send` hook: drop cookies, headers, bodies, user data; mask text fields."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("cookies", None)
        request.pop("data", None)
        request.pop("query_string", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                k: ("[redacted]" if k.lower() in _SENSITIVE_HEADERS else _scrub_text(v))
                for k, v in headers.items()
            }
    event.pop("user", None)
    event["message"] = _scrub_text(event.get("message"))
    for exc in (event.get("exception") or {}).get("values") or []:
        exc["value"] = _scrub_text(exc.get("value"))
    for crumb in (event.get("breadcrumbs") or {}).get("values") or []:
        crumb["message"] = _scrub_text(crumb.get("message"))
        crumb.pop("data", None)
    return event


def init_sentry(dsn: str, *, environment: str, traces_sample_rate: float = 0.0) -> bool:
    """Start Sentry when a DSN is given and the package is installed. Returns True if started."""
    if not dsn:
        return False
    try:
        import sentry_sdk  # pyright: ignore[reportMissingImports]  (optional dependency)
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; error reporting is off")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        send_default_pii=False,
        traces_sample_rate=traces_sample_rate,
        before_send=scrub_event,
        max_request_body_size="never",
        include_local_variables=False,
    )
    return True

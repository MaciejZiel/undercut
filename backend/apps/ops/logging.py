"""Logging helpers: request id context, redaction filter and a JSON-lines formatter.

Standard library only, so production logging works without extra dependencies.
"""

import contextvars
import json
import logging
from datetime import UTC, datetime

from .redaction import redact

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

# Extra fields a log call may attach (`logger.info("...", extra={"status": 200})`).
_EXTRA_FIELDS = ("method", "path", "status", "duration_ms")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class RedactionFilter(logging.Filter):
    """Masks secrets and e-mail addresses in the message of every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        for name in _EXTRA_FIELDS:
            value = getattr(record, name, None)
            if isinstance(value, str):
                setattr(record, name, redact(value))
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line: time, level, logger, message, request id, exception."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": getattr(record, "request_id", "") or request_id_var.get(),
        }
        for name in _EXTRA_FIELDS:
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        elif record.exc_text:
            payload["exception"] = redact(record.exc_text)
        return json.dumps(payload, ensure_ascii=False, default=str)

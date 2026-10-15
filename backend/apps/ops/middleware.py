import logging
import re
import time
import uuid

from .logging import request_id_var

logger = logging.getLogger("undercut.request")

# Only accept ids that are safe to log and echo (no newlines, bounded length).
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_QUIET_PATHS = frozenset({"/api/health/", "/api/ready/"})


class RequestIdMiddleware:
    """Reads or creates X-Request-ID, echoes it, and writes one access line per request.

    The query string is never logged, and a resolved URL is logged as its route pattern
    (`.../unsubscribe/<str:token>/`), because tokens also travel in paths.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get("HTTP_X_REQUEST_ID", "")
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.monotonic()
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            response["X-Request-ID"] = request_id
            return response
        finally:
            if request.path not in _QUIET_PATHS:
                match = request.resolver_match
                path = f"/{match.route}" if match is not None else request.path[:200]
                logger.info(
                    "%s %s %s",
                    request.method,
                    path,
                    status,
                    extra={
                        "method": request.method,
                        "path": path,
                        "status": status,
                        "duration_ms": round((time.monotonic() - started) * 1000, 1),
                    },
                )
            request_id_var.reset(token)

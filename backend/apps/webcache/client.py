"""Ask the Next.js frontend to purge cached pages by tag (POST /_internal/revalidate)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable

from django.conf import settings

log = logging.getLogger(__name__)

MAX_TAGS_PER_REQUEST = 100  # the frontend rejects more
TIMEOUT = 5


class RevalidateError(Exception):
    """The frontend refused or could not be reached; the outbox retries the event."""


def _post(url: str, secret: str, tags: list[str]) -> int:
    request = urllib.request.Request(
        url,
        data=json.dumps({"tags": tags}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "x-revalidate-secret": secret},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RevalidateError(f"Frontend unreachable: {exc}") from exc


def revalidate(
    tags: Iterable[str], *, post: Callable[[str, str, list[str]], int] | None = None
) -> int:
    """Purge tags. Returns how many were sent; 0 when revalidation is not configured."""
    unique = sorted(set(tags))
    url = getattr(settings, "REVALIDATE_URL", "")
    secret = getattr(settings, "REVALIDATE_SECRET", "")
    if not unique:
        return 0
    if not url or not secret:
        log.info("Revalidation not configured, skipping %s tags", len(unique))
        return 0
    for start in range(0, len(unique), MAX_TAGS_PER_REQUEST):
        chunk = unique[start : start + MAX_TAGS_PER_REQUEST]
        status = (post or _post)(url, secret, chunk)  # resolved late so tests can patch _post
        if status != 200:
            raise RevalidateError(f"Frontend answered HTTP {status}")
    return len(unique)

"""HTTP client for the Jolpica-F1 (Ergast-compatible) API.

Jolpica is a free service run by volunteers: the client stays well inside the documented
limits (4 requests/s, 500/hour), identifies itself, backs off on 429/5xx and never loops.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from collections.abc import Callable
from functools import lru_cache

log = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1/"
USER_AGENT = "Undercut/0.1 (+https://undercut.maciejzielinski.dev)"
MAX_BYTES = 8_000_000
TIMEOUT = 20
MAX_RETRY_AFTER = 60

Fetch = Callable[[str], tuple[int, dict[str, str], bytes]]


class JolpicaError(Exception):
    """The API could not be read (after retries)."""


class RateLimiter:
    """Sliding window: at most `calls` acquisitions per `period` seconds."""

    def __init__(self, calls: int, period: float, *, clock=time.monotonic, sleep=time.sleep):
        self.calls, self.period = calls, period
        self._clock, self._sleep = clock, sleep
        self._stamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                while self._stamps and now - self._stamps[0] >= self.period:
                    self._stamps.popleft()
                if len(self._stamps) < self.calls:
                    self._stamps.append(now)
                    return
                wait = self.period - (now - self._stamps[0])
            self._sleep(max(wait, 0.01))


def _urlopen(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            return response.status, dict(response.headers), response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise JolpicaError(f"Network error: {exc}") from exc


class JolpicaClient:
    def __init__(
        self,
        *,
        fetch: Fetch = _urlopen,
        limiters: list[RateLimiter] | None = None,
        sleep=time.sleep,
        max_attempts: int = 4,
        base_delay: float = 2.0,
    ):
        self._fetch = fetch
        # 80% of the published limits (4/s and 500/h).
        self._limiters = (
            limiters
            if limiters is not None
            else [
                RateLimiter(3, 1.0),
                RateLimiter(400, 3600.0),
            ]
        )
        self._sleep = sleep
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.requests_made = 0

    def get(self, path: str, **params) -> dict:
        """GET a path below the Ergast root and return the `MRData` object."""
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{BASE_URL}{path.strip('/')}/" + (f"?{query}" if query else "")
        last = ""
        for attempt in range(1, self.max_attempts + 1):
            for limiter in self._limiters:
                limiter.acquire()
            self.requests_made += 1
            try:
                status, headers, body = self._fetch(url)
            except JolpicaError as exc:
                last = str(exc)
            else:
                if status == 200:
                    return self._decode(body, url)
                last = f"HTTP {status}"
                if status != 429 and status < 500:
                    raise JolpicaError(f"{last} for {url}")
                if status == 429:
                    self._sleep(min(self._retry_after(headers), MAX_RETRY_AFTER))
                    continue
            if attempt < self.max_attempts:
                delay = self.base_delay * 2 ** (attempt - 1)
                log.warning("Jolpica %s (attempt %s), retrying in %.0fs", last, attempt, delay)
                self._sleep(delay)
        raise JolpicaError(f"Giving up on {url}: {last}")

    @staticmethod
    def _retry_after(headers: dict[str, str]) -> float:
        for key, value in headers.items():
            if key.lower() == "retry-after":
                try:
                    return max(float(value), 1.0)
                except ValueError:
                    break
        return 10.0

    @staticmethod
    def _decode(body: bytes, url: str) -> dict:
        if len(body) > MAX_BYTES:
            raise JolpicaError(f"Response too large for {url}")
        try:
            return json.loads(body)["MRData"]
        except (ValueError, KeyError, TypeError) as exc:
            raise JolpicaError(f"Unexpected response for {url}") from exc

    # ----------------------------------------------------------------- endpoints

    def schedule(self, year: int) -> dict:
        return self.get(f"{year}/races", limit=100)

    def results(self, year: int, number: int) -> dict:
        return self.get(f"{year}/{number}/results", limit=100)

    def sprint(self, year: int, number: int) -> dict:
        return self.get(f"{year}/{number}/sprint", limit=100)

    def qualifying(self, year: int, number: int) -> dict:
        return self.get(f"{year}/{number}/qualifying", limit=100)

    def driver_standings(self, year: int, number: int) -> dict:
        return self.get(f"{year}/{number}/driverstandings", limit=100)

    def constructor_standings(self, year: int, number: int) -> dict:
        return self.get(f"{year}/{number}/constructorstandings", limit=100)


@lru_cache(maxsize=1)
def shared_client() -> JolpicaClient:
    """One process-wide client so every handler shares the same rate-limit window."""
    return JolpicaClient()

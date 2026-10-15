"""HTTP client for the OpenF1 REST API.

Behaviour worth knowing:
- an empty result is HTTP 404 on OpenF1, mapped here to an empty list;
- requests are paced by token buckets set to 80% of the free limits (3 req/s, 30 req/min);
- 429, 5xx and network errors are retried with exponential backoff (Retry-After is honoured);
- an optional Bearer token comes from the OPENF1_TOKEN environment variable and is never logged
  or put into exception messages or `repr`.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import quote

log = logging.getLogger(__name__)

BASE_URL = "https://api.openf1.org/v1/"
USER_AGENT = "Undercut/0.1 (+https://undercut.maciejzielinski.dev)"
TOKEN_ENV = "OPENF1_TOKEN"

FREE_PER_SECOND = 3.0
FREE_PER_MINUTE = 30.0
SAFETY_FACTOR = 0.8

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_BYTES = 32 * 1024 * 1024
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_OPERATORS = ("<=", ">=", "<", ">")


class OpenF1Error(RuntimeError):
    """The API failed in a way retrying did not fix."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


class ResponseTooLarge(OpenF1Error):
    """The body exceeded the size cap; callers may retry with a narrower filter."""


_EPSILON = 1e-9


class TokenBucket:
    """Refills at `rate` tokens per second up to `capacity`; `acquire` blocks until one is free."""

    def __init__(
        self,
        rate: float,
        capacity: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if rate <= 0 or capacity < 1:
            raise ValueError("rate must be positive and capacity at least 1")
        self.rate = rate
        self.capacity = capacity
        self._clock = clock
        self._sleep = sleep
        self._tokens = capacity
        self._stamp = clock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self.capacity, self._tokens + (now - self._stamp) * self.rate)
        self._stamp = now

    def acquire(self) -> float:
        """Take one token, sleeping as needed. Returns the time slept."""
        slept = 0.0
        self._refill()
        while self._tokens < 1:
            wait = (1 - self._tokens) / self.rate
            self._sleep(wait)
            slept += wait
            self._refill()
            # After waiting exactly long enough, rounding can leave the bucket a hair under 1.
            # Without this tolerance the next wait is ~1e-16 s, a clock may not advance by that
            # little, and the loop would never end.
            if self._tokens > 1 - _EPSILON:
                self._tokens = 1.0
        self._tokens -= 1
        return slept


class RateLimiter:
    """Both limits at once. The minute bucket's burst is limit minus its refill over a minute,
    so that any 60 s window holds at most `per_minute * safety` requests plus that burst, which
    stays within the real limit."""

    def __init__(
        self,
        per_second: float = FREE_PER_SECOND,
        per_minute: float = FREE_PER_MINUTE,
        safety: float = SAFETY_FACTOR,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        sec_rate = per_second * safety
        min_rate = per_minute * safety / 60
        self.second = TokenBucket(
            sec_rate, max(1, math.floor(per_second - sec_rate)), clock=clock, sleep=sleep
        )
        self.minute = TokenBucket(
            min_rate, max(1, math.floor(per_minute - min_rate * 60)), clock=clock, sleep=sleep
        )

    @classmethod
    def from_env(cls, **kwargs) -> RateLimiter:
        """Limits can be raised for a paid plan: OPENF1_RATE_PER_SECOND / OPENF1_RATE_PER_MINUTE."""
        per_second = float(os.environ.get("OPENF1_RATE_PER_SECOND", FREE_PER_SECOND))
        per_minute = float(os.environ.get("OPENF1_RATE_PER_MINUTE", FREE_PER_MINUTE))
        return cls(per_second, per_minute, **kwargs)

    def acquire(self) -> float:
        return self.minute.acquire() + self.second.acquire()


def build_query(params: Mapping[str, Any] | None) -> str:
    """`{"session_key": 9472, "date>=": "2024-03-02T15:00:00"}` -> `session_key=9472&date>=...`.

    A key ending in <, >, <= or >= is a comparison filter in OpenF1's own syntax.
    """
    parts = []
    for key, value in (params or {}).items():
        op = next((o for o in _OPERATORS if key.endswith(o)), None)
        text = quote(str(value), safe=":")
        if op:
            parts.append(f"{quote(key[: -len(op)], safe='_')}{op}{text}")
        else:
            parts.append(f"{quote(key, safe='_')}={text}")
    return "&".join(parts)


Opener = Callable[..., Any]


class OpenF1Client:
    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        token: str | None = None,
        limiter: RateLimiter | None = None,
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 5,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
        timeout: float = DEFAULT_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self._token = token or os.environ.get(TOKEN_ENV) or None
        self._sleep = sleep
        self.limiter = limiter or RateLimiter.from_env(sleep=sleep)
        self._opener = opener or urllib.request.urlopen
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.requests = 0  # HTTP requests actually sent, retries included
        self.by_endpoint: Counter[str] = Counter()

    def __repr__(self) -> str:
        return f"OpenF1Client(base_url={self.base_url!r}, authenticated={bool(self._token)})"

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _backoff(self, attempt: int, retry_after: str | None = None) -> float:
        if retry_after:
            try:
                return min(float(retry_after), self.backoff_max)
            except ValueError:
                pass
        return min(self.backoff_base * 2**attempt, self.backoff_max)

    def _read(self, response) -> bytes:
        body = response.read(self.max_bytes + 1)
        if len(body) > self.max_bytes:
            raise ResponseTooLarge(f"response larger than {self.max_bytes} bytes")
        return body

    def get(self, endpoint: str, params: Mapping[str, Any] | None = None) -> list[dict]:
        """GET `endpoint` with filters; returns a list of rows ([] when OpenF1 says 404)."""
        endpoint = endpoint.strip("/")
        query = build_query(params)
        url = f"{self.base_url}{endpoint}" + (f"?{query}" if query else "")
        last_error = "no attempt made"
        for attempt in range(self.max_retries + 1):
            self.limiter.acquire()
            self.requests += 1
            self.by_endpoint[endpoint] += 1
            retry_after = None
            try:
                request = urllib.request.Request(url, headers=self._headers())
                with self._opener(request, timeout=self.timeout) as response:
                    body = self._read(response)
                return self._decode(body, url)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return []
                if exc.code not in RETRYABLE_STATUSES:
                    raise OpenF1Error(f"HTTP {exc.code} for {url}", status=exc.code) from None
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                last_error = f"HTTP {exc.code}"
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                last_error = type(exc).__name__
            if attempt < self.max_retries:
                delay = self._backoff(attempt, retry_after)
                log.warning("OpenF1 %s for %s, retrying in %.1fs", last_error, endpoint, delay)
                self._sleep(delay)
        raise OpenF1Error(f"{last_error} for {url} after {self.max_retries + 1} attempts")

    @staticmethod
    def _decode(body: bytes, url: str) -> list[dict]:
        try:
            data = json.loads(body)
        except ValueError as exc:
            raise OpenF1Error(f"invalid JSON from {url}") from exc
        if not isinstance(data, list):
            raise OpenF1Error(f"expected a JSON list from {url}")
        return [row for row in data if isinstance(row, dict)]

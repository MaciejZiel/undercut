import io
import json
import logging
import urllib.error

import pytest

from apps.ingestion.openf1.client import (
    USER_AGENT,
    OpenF1Client,
    OpenF1Error,
    RateLimiter,
    ResponseTooLarge,
    TokenBucket,
    build_query,
)


class Resp:
    def __init__(self, body: bytes):
        self._body = io.BytesIO(body)

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, headers=None):
    from email.message import Message

    msg = Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return urllib.error.HTTPError("https://x", code, "err", msg, io.BytesIO(b"{}"))


class Script:
    """An opener that plays back a list of responses or exceptions."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return Resp(json.dumps(step).encode() if not isinstance(step, bytes) else step)


class FakeTime:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        # Guard: a limiter that never makes progress must fail fast instead of eating memory.
        assert len(self.sleeps) < 10_000, "limiter is spinning"
        self.now += seconds


def make_client(*steps, **kwargs):
    t = FakeTime()
    limiter = RateLimiter(clock=t.clock, sleep=t.sleep)
    opener = Script(*steps)
    client = OpenF1Client(limiter=limiter, opener=opener, sleep=t.sleep, **kwargs)
    return client, opener, t


def test_build_query_supports_comparison_filters():
    query = build_query({"session_key": 9472, "date>=": "2024-03-02T15:00:00", "date<": "x y"})
    assert query == "session_key=9472&date>=2024-03-02T15:00:00&date<x%20y"


def test_get_returns_rows_and_sends_user_agent():
    client, opener, _ = make_client([{"a": 1}, "junk"])
    assert client.get("laps", {"session_key": 1}) == [{"a": 1}]
    request, timeout = opener.requests[0]
    assert request.full_url == "https://api.openf1.org/v1/laps?session_key=1"
    assert request.get_header("User-agent") == USER_AGENT
    assert request.get_header("Authorization") is None
    assert timeout == client.timeout
    assert client.requests == 1 and client.by_endpoint["laps"] == 1


def test_404_means_empty_result_without_retry():
    client, opener, _ = make_client(http_error(404))
    assert client.get("intervals", {"session_key": 1}) == []
    assert len(opener.requests) == 1


@pytest.mark.parametrize("code", [429, 500, 503])
def test_retries_with_exponential_backoff(code):
    client, opener, t = make_client(http_error(code), http_error(code), [{"ok": 1}])
    assert client.get("pit") == [{"ok": 1}]
    assert len(opener.requests) == 3 and client.requests == 3
    backoffs = [x for x in t.sleeps if x >= 2]
    assert backoffs[:2] == [2.0, 4.0]


def test_retry_after_header_is_honoured():
    client, _, t = make_client(http_error(429, {"Retry-After": "7"}), [])
    assert client.get("pit") == []
    assert 7.0 in t.sleeps


def test_gives_up_after_max_retries():
    client, opener, _ = make_client(*[http_error(500)] * 3, max_retries=2)
    with pytest.raises(OpenF1Error, match="HTTP 500"):
        client.get("pit")
    assert len(opener.requests) == 3


def test_network_error_is_retried():
    client, _, _ = make_client(urllib.error.URLError("down"), [{"x": 1}])
    assert client.get("pit") == [{"x": 1}]


def test_other_4xx_fail_immediately():
    client, opener, _ = make_client(http_error(401))
    with pytest.raises(OpenF1Error) as exc:
        client.get("pit")
    assert exc.value.status == 401 and len(opener.requests) == 1


def test_size_cap():
    client, _, _ = make_client(b"[" + b" " * 100 + b"]", max_bytes=50)
    with pytest.raises(ResponseTooLarge):
        client.get("position")


def test_non_list_json_is_an_error():
    client, _, _ = make_client({"detail": "x"})
    with pytest.raises(OpenF1Error):
        client.get("pit")


def test_token_is_sent_but_never_leaked(monkeypatch, caplog):
    secret = "s3cr3t-token-value"
    monkeypatch.setenv("OPENF1_TOKEN", secret)
    client, opener, _ = make_client(http_error(500), http_error(401))
    with caplog.at_level(logging.DEBUG), pytest.raises(OpenF1Error) as exc:
        client.get("pit")
    request, _ = opener.requests[0]
    assert request.get_header("Authorization") == f"Bearer {secret}"
    assert secret not in str(exc.value)
    assert secret not in repr(client)
    assert secret not in caplog.text


def test_no_token_by_default(monkeypatch):
    monkeypatch.delenv("OPENF1_TOKEN", raising=False)
    client, opener, _ = make_client([])
    client.get("pit")
    assert opener.requests[0][0].get_header("Authorization") is None


def test_token_bucket_blocks_until_refilled():
    t = FakeTime()
    bucket = TokenBucket(rate=2.0, capacity=2, clock=t.clock, sleep=t.sleep)
    assert bucket.acquire() == 0 and bucket.acquire() == 0
    assert bucket.acquire() == pytest.approx(0.5)


def test_limiter_stays_under_80_percent_of_the_free_limits():
    t = FakeTime()
    limiter = RateLimiter(clock=t.clock, sleep=t.sleep)
    stamps = []
    for _ in range(120):
        limiter.acquire()
        stamps.append(t.now)
    for i, start in enumerate(stamps):
        in_second = sum(1 for s in stamps[i:] if s < start + 1)
        in_minute = sum(1 for s in stamps[i:] if s < start + 60)
        assert in_second <= 3
        assert in_minute <= 30
    # long run: about 24 requests a minute
    rate = (len(stamps) - 6) / (stamps[-1] - stamps[0]) * 60
    assert rate == pytest.approx(24, rel=0.05)

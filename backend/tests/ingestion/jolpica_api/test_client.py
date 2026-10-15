import json

import pytest

from apps.ingestion.jolpica.client import JolpicaClient, JolpicaError, RateLimiter


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        assert len(self.sleeps) < 5000, "limiter is spinning"  # fail fast, never eat memory
        self.now += max(seconds, 0.001)


def ok(payload):
    return 200, {}, json.dumps({"MRData": payload}).encode()


def make(*responses, clock=None, **kwargs):
    clock = clock or Clock()
    script = list(responses)
    urls = []

    def fetch(url):
        urls.append(url)
        assert len(urls) < 50, "client is looping"
        return script.pop(0)

    limiters = [RateLimiter(3, 1.0, clock=clock.time, sleep=clock.sleep)]
    client = JolpicaClient(fetch=fetch, limiters=limiters, sleep=clock.sleep, **kwargs)
    return client, urls, clock


def test_get_returns_mrdata_and_builds_the_url():
    client, urls, _ = make(ok({"total": "1"}))
    assert client.get("2024/1/results", limit=100) == {"total": "1"}
    assert urls == ["https://api.jolpi.ca/ergast/f1/2024/1/results/?limit=100"]


def test_rate_limiter_spreads_a_burst():
    clock = Clock()
    client, _, _ = make(*[ok({}) for _ in range(7)], clock=clock)
    for _ in range(7):
        client.get("seasons")
    # three per second: the 7 calls cannot fit inside less than two seconds
    assert clock.now >= 2.0


def test_429_waits_for_retry_after_then_succeeds():
    client, urls, clock = make((429, {"Retry-After": "7"}, b""), ok({"ok": 1}))
    assert client.get("seasons") == {"ok": 1}
    assert len(urls) == 2
    assert 7 in clock.sleeps


def test_server_errors_are_retried_with_backoff_then_give_up():
    client, urls, clock = make(*[(503, {}, b"") for _ in range(4)], max_attempts=4, base_delay=2.0)
    with pytest.raises(JolpicaError, match="Giving up"):
        client.get("seasons")
    assert len(urls) == 4
    assert [s for s in clock.sleeps if s >= 2] == [2.0, 4.0, 8.0]


def test_client_errors_are_not_retried():
    client, urls, _ = make((404, {}, b"nope"))
    with pytest.raises(JolpicaError, match="HTTP 404"):
        client.get("2099/1/results")
    assert len(urls) == 1


def test_unexpected_payload_is_an_error():
    client, _, _ = make((200, {}, b"<html>"))
    with pytest.raises(JolpicaError, match="Unexpected response"):
        client.get("seasons")

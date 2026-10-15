"""NFR-202: 5 failed logins per 15 minutes per IP and per account (cache based)."""

import pytest
from django.conf import settings

from .conftest import ALLAUTH
from .factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

LOGIN = f"{ALLAUTH}/auth/login"


def attempt(client, email, password="wrong-password-123", ip="10.0.0.1"):
    return client.post(LOGIN, {"email": email, "password": password}, format="json", REMOTE_ADDR=ip)


def codes(resp):
    return [e["code"] for e in resp.json().get("errors", [])]


def is_throttled(resp):
    """allauth answers a throttled login with a 400 carrying this error code."""
    return resp.status_code == 400 and "too_many_login_attempts" in codes(resp)


def test_configured_limit():
    assert settings.ACCOUNT_RATE_LIMITS["login_failed"] == "5/15m/ip,5/15m/key"


def test_sixth_attempt_for_one_account_is_throttled(client):
    user = UserFactory()
    for _ in range(5):
        resp = attempt(client, user.email)
        assert resp.status_code == 400
        assert not is_throttled(resp)
    assert is_throttled(attempt(client, user.email))


def test_account_stays_locked_even_with_the_correct_password(client):
    user = UserFactory()
    for _ in range(5):
        attempt(client, user.email)
    assert is_throttled(attempt(client, user.email, password=PASSWORD))


def test_limit_is_per_account_across_ips(client):
    user = UserFactory()
    for i in range(5):
        attempt(client, user.email, ip=f"10.0.1.{i}")
    assert is_throttled(attempt(client, user.email, ip="10.0.2.1"))


def test_limit_is_per_ip_across_accounts(client):
    users = UserFactory.create_batch(6)
    for user in users[:5]:
        assert not is_throttled(attempt(client, user.email, ip="10.0.3.1"))
    # A sixth, different account from the same address is refused.
    assert is_throttled(attempt(client, users[5].email, ip="10.0.3.1"))
    # Another visitor can still log in to that account.
    assert attempt(client, users[5].email, password=PASSWORD, ip="10.0.3.2").status_code == 200


def test_other_accounts_are_not_affected_by_one_locked_account(client):
    locked, other = UserFactory.create_batch(2)
    for i in range(5):
        attempt(client, locked.email, ip=f"10.0.4.{i}")
    assert attempt(client, other.email, password=PASSWORD, ip="10.0.5.1").status_code == 200


def test_successful_logins_do_not_count_against_the_limit(client):
    user = UserFactory()
    for _ in range(6):
        assert attempt(client, user.email, password=PASSWORD).status_code == 200
        client.delete(f"{ALLAUTH}/auth/session")


def test_lock_expires_after_fifteen_minutes(client, monkeypatch):
    import time as real_time
    from types import SimpleNamespace

    from allauth.core.internal import ratelimit

    user = UserFactory()
    for _ in range(5):
        attempt(client, user.email)
    assert is_throttled(attempt(client, user.email, password=PASSWORD))

    now = real_time.time()
    # Only the wall clock moves forward; allauth also uses monotonic()/sleep() for cache locks.
    shifted = SimpleNamespace(
        time=lambda: now + 15 * 60 + 1,
        monotonic=real_time.monotonic,
        sleep=real_time.sleep,
    )
    monkeypatch.setattr(ratelimit, "time", shifted)
    assert attempt(client, user.email, password=PASSWORD).status_code == 200

import datetime as dt

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.predictions import locking

from .factories import make_drivers, make_user, make_weekend

NOW = dt.datetime(2025, 3, 14, 12, 0, tzinfo=dt.UTC)


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def clock(monkeypatch):
    """Controllable server clock: clock.now = ..."""

    class Clock:
        now = NOW

    monkeypatch.setattr(locking, "now", lambda: Clock.now)
    return Clock


@pytest.fixture
def user(db):
    return make_user()


@pytest.fixture
def drivers(db):
    return make_drivers(6)


@pytest.fixture
def weekend(db, clock):
    """Open round 2025/1: qualifying starts 1 hour after NOW."""
    return make_weekend(2025, 1, quali_start=NOW + dt.timedelta(hours=1))


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def anon():
    return APIClient()

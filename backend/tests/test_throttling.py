import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.throttling import PublicAnonRateThrottle

URL = "/api/v1/seasons/"


@pytest.fixture(autouse=True)
def tight_limit(monkeypatch):
    cache.clear()
    monkeypatch.setattr(PublicAnonRateThrottle, "THROTTLE_RATES", {"anon": "3/min"})
    yield
    cache.clear()


def hits(client, count, **headers):
    return [client.get(URL, **headers).status_code for _ in range(count)]


@pytest.mark.django_db
def test_visitors_are_limited():
    assert hits(APIClient(), 5) == [200, 200, 200, 429, 429]


@pytest.mark.django_db
@override_settings(INTERNAL_API_TOKEN="s3cret")
def test_requests_with_the_internal_token_are_not_limited():
    assert set(hits(APIClient(), 10, HTTP_X_INTERNAL_TOKEN="s3cret")) == {200}


@pytest.mark.django_db
@override_settings(INTERNAL_API_TOKEN="s3cret")
def test_a_wrong_token_is_limited_like_anyone_else():
    assert hits(APIClient(), 5, HTTP_X_INTERNAL_TOKEN="guess") == [200, 200, 200, 429, 429]


@pytest.mark.django_db
@override_settings(INTERNAL_API_TOKEN="")
def test_an_unset_token_never_matches_an_empty_header():
    assert hits(APIClient(), 5, HTTP_X_INTERNAL_TOKEN="") == [200, 200, 200, 429, 429]


@pytest.mark.django_db
@override_settings(INTERNAL_API_TOKEN="s3cret")
def test_internal_traffic_does_not_use_up_the_visitors_budget():
    hits(APIClient(), 10, HTTP_X_INTERNAL_TOKEN="s3cret")
    assert hits(APIClient(), 3) == [200, 200, 200]

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts import exports

from .factories import UserFactory

ALLAUTH = "/api/v1/allauth/browser/v1"


@pytest.fixture(autouse=True)
def _clean_cache():
    """Rate limits live in the cache; every test starts with fresh counters."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.force_login(user)
    return c


@pytest.fixture
def isolated_exports():
    """Restore the export provider registry after a test that registers its own providers."""
    before = dict(exports._providers)
    yield
    exports._providers.clear()
    exports._providers.update(before)

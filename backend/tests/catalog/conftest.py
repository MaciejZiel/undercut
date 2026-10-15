import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    cache.clear()
    yield
    cache.clear()

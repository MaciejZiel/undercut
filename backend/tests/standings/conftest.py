import pytest
from rest_framework.test import APIClient

from apps.standings.api import views


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(views.StandingsView, "throttle_classes", [])
    monkeypatch.setattr(views.ProgressView, "throttle_classes", [])


@pytest.fixture
def client():
    return APIClient()

from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.events.models import OutboxEvent

pytestmark = pytest.mark.django_db


def test_health_stays_a_cheap_db_ping(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(client):
    response = client.get(reverse("ready"))
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": True, "migrations": True, "outbox": True},
    }


def test_ready_fails_when_outbox_has_dead_events(client, make_event):
    make_event(status=OutboxEvent.Status.DEAD)
    response = client.get(reverse("ready"))
    assert response.status_code == 503
    assert response.json()["checks"]["outbox"] is False
    # Public endpoint: no counts or event details leak.
    assert "dead" not in response.content.decode()


def test_ready_fails_on_unapplied_migrations(client, monkeypatch):
    class Plan:
        def __init__(self, connection):
            self.loader = type("L", (), {"graph": type("G", (), {"leaf_nodes": lambda s: []})()})()

        def migration_plan(self, targets):
            return [("fake", False)]

    monkeypatch.setattr("apps.ops.views.MigrationExecutor", Plan)
    response = client.get(reverse("ready"))
    assert response.status_code == 503
    assert response.json()["checks"]["migrations"] is False


def test_ready_reports_unreachable_database(client, monkeypatch):
    monkeypatch.setattr("apps.ops.views._database_ok", lambda: False)
    response = client.get(reverse("ready"))
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": False, "migrations": False, "outbox": False}


def test_status_requires_staff():
    client = APIClient()
    url = reverse("ops-status")
    assert client.get(url).status_code in (401, 403)
    user = User.objects.create_user(username="plain", password="x" * 12)
    client.force_login(user)
    assert client.get(url).status_code == 403


def test_status_for_staff(make_event, healthy_heartbeats, make_race):
    make_event(age=timedelta(minutes=3))
    make_race(ended_ago=timedelta(hours=1))
    staff = User.objects.create_user(username="ops", password="x" * 12, is_staff=True)
    client = APIClient()
    client.force_login(staff)
    response = client.get(reverse("ops-status"))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "generated_at",
        "outbox",
        "sync_runs",
        "heartbeats",
        "freshness",
        "tables",
    }
    assert body["outbox"]["pending"] == 1
    assert {h["name"] for h in body["heartbeats"]} == {"scheduler", "outbox-worker"}
    assert body["freshness"]["latest_race"]["results_final"] is False

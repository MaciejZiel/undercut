import pytest
from django.core.management import call_command

from apps.ops import heartbeat
from apps.ops.models import Heartbeat

pytestmark = pytest.mark.django_db


def test_beat_creates_then_updates_one_row():
    assert heartbeat.beat("scheduler", force=True) is True
    first = Heartbeat.objects.get(name="scheduler").beat_at
    assert heartbeat.beat("scheduler", force=True) is True
    assert Heartbeat.objects.filter(name="scheduler").count() == 1
    assert Heartbeat.objects.get(name="scheduler").beat_at >= first


def test_beat_is_throttled():
    assert heartbeat.beat("scheduler") is True
    assert heartbeat.beat("scheduler") is False


def test_beat_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(Heartbeat.objects, "update_or_create", boom)
    assert heartbeat.beat("scheduler", force=True) is False


def test_worker_and_scheduler_commands_beat():
    call_command("run_outbox_worker", "--once")
    call_command("run_scheduler", "--once")
    assert set(Heartbeat.objects.values_list("name", flat=True)) == {"outbox-worker", "scheduler"}

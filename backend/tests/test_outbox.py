from datetime import timedelta

import pytest
from django.db import transaction
from django.utils import timezone

from apps.events import registry
from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.worker import MAX_ATTEMPTS, process_batch


@pytest.fixture(autouse=True)
def clean_registry():
    registry.clear()
    yield
    registry.clear()


@pytest.mark.django_db(transaction=True)
def test_publish_outside_a_transaction_is_rejected():
    with pytest.raises(RuntimeError, match="transaction"):
        publish("Ping")
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_publish_inside_a_transaction_records_a_pending_event():
    event = publish("Ping", key="k", payload={"id": 1})
    assert event.status == OutboxEvent.Status.PENDING


@pytest.mark.django_db
def test_rolled_back_transaction_leaves_no_event():
    with pytest.raises(RuntimeError), transaction.atomic():
        publish("Ping")
        raise RuntimeError("boom")
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_worker_delivers_event_to_subscribers():
    seen = []
    registry.subscribe("Ping")(lambda e: seen.append(e.payload["id"]))
    publish("Ping", payload={"id": 7})

    assert process_batch() == 1

    assert seen == [7]
    event = OutboxEvent.objects.get()
    assert event.status == OutboxEvent.Status.DONE
    assert event.processed_at is not None


@pytest.mark.django_db
def test_delivering_the_same_event_twice_is_safe_for_idempotent_handlers():
    """At-least-once delivery: a re-delivered event must not change the outcome."""
    state = {"points": 0}

    def recompute(_event):
        state["points"] = 25  # "recompute for this session", not "add 25"

    registry.subscribe("SessionResultsFinalized")(recompute)
    publish("SessionResultsFinalized", key="session:1")
    process_batch()
    publish("SessionResultsFinalized", key="session:1")  # correction after the race
    process_batch()

    assert state["points"] == 25


@pytest.mark.django_db
def test_failing_handler_is_retried_with_backoff_then_goes_dead():
    def always_fails(_event):
        raise ValueError("nope")

    registry.subscribe("Ping")(always_fails)
    event = publish("Ping")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        OutboxEvent.objects.filter(pk=event.pk).update(available_at=timezone.now())
        process_batch()
        event.refresh_from_db()
        assert event.attempts == attempt

    assert event.status == OutboxEvent.Status.DEAD
    assert "ValueError: nope" in event.last_error


@pytest.mark.django_db
def test_failed_event_is_not_due_until_backoff_elapses():
    registry.subscribe("Ping")(lambda e: 1 / 0)
    event = publish("Ping")
    process_batch()
    event.refresh_from_db()
    assert event.available_at > timezone.now() + timedelta(seconds=1)
    assert process_batch() == 0


@pytest.mark.django_db
def test_events_with_the_same_key_wait_for_an_earlier_failure():
    delivered = []

    def handler(event):
        if event.payload["n"] == 1:
            raise ValueError("first fails")
        delivered.append(event.payload["n"])

    registry.subscribe("Step")(handler)
    publish("Step", key="session:1", payload={"n": 1})
    publish("Step", key="session:1", payload={"n": 2})
    publish("Step", key="session:2", payload={"n": 3})

    process_batch()

    assert delivered == [3]  # same-key successor is held back, other keys proceed


@pytest.mark.django_db
def test_future_events_are_not_delivered_early():
    registry.subscribe("Later")(lambda e: pytest.fail("delivered too early"))
    publish("Later", available_at=timezone.now() + timedelta(hours=1))
    assert process_batch() == 0


@pytest.mark.django_db
def test_retry_runs_only_the_handlers_that_failed():
    calls = {"good": 0, "flaky": 0}

    def good(_event):
        calls["good"] += 1

    def flaky(_event):
        calls["flaky"] += 1
        if calls["flaky"] == 1:
            raise ValueError("first time fails")

    registry.subscribe("Ping")(good)
    registry.subscribe("Ping")(flaky)
    event = publish("Ping")

    process_batch()
    event.refresh_from_db()
    assert (calls, event.status, len(event.delivered)) == (
        {"good": 1, "flaky": 1},
        OutboxEvent.Status.PENDING,
        1,
    )

    OutboxEvent.objects.filter(pk=event.pk).update(available_at=timezone.now())
    process_batch()
    event.refresh_from_db()

    assert calls == {"good": 1, "flaky": 2}  # the good handler was NOT run again
    assert event.status == OutboxEvent.Status.DONE


@pytest.mark.django_db
def test_a_failing_handler_does_not_stop_the_others():
    seen = []
    registry.subscribe("Ping")(lambda e: 1 / 0)
    registry.subscribe("Ping")(lambda e: seen.append("second"))
    publish("Ping")

    process_batch()

    assert seen == ["second"]


@pytest.mark.django_db
def test_two_lambdas_on_one_event_are_tracked_separately():
    seen = []
    registry.subscribe("Ping")(lambda e: seen.append("a"))
    registry.subscribe("Ping")(lambda e: seen.append("b"))
    publish("Ping")

    process_batch()

    assert sorted(seen) == ["a", "b"]

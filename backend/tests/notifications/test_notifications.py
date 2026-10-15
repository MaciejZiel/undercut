import pytest
from django.apps import apps
from django.db import IntegrityError

from apps.events import registry
from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.worker import process_batch
from apps.notifications import handlers, services
from apps.notifications.models import NotificationPref
from tests.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def url(token):
    return f"/api/v1/notifications/unsubscribe/{token}/"


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def subscribed(user):
    services.set_race_result_email(user, True)
    return services.get_pref(user)


def test_preference_defaults_to_off(user):
    pref = services.get_pref(user)
    assert pref.race_result_email is False
    assert len(pref.unsubscribe_token) >= 32


def test_tokens_are_unique_per_user():
    a, b = UserFactory.create_batch(2)
    assert services.get_pref(a).unsubscribe_token != services.get_pref(b).unsubscribe_token
    with pytest.raises(IntegrityError):
        NotificationPref.objects.filter(user=b).update(
            unsubscribe_token=services.get_pref(a).unsubscribe_token
        )


def test_get_pref_is_idempotent(user):
    assert services.get_pref(user).pk == services.get_pref(user).pk
    assert NotificationPref.objects.count() == 1


def test_race_result_email_enabled_does_not_create_rows(user):
    assert services.race_result_email_enabled(user) is False
    assert NotificationPref.objects.count() == 0


@pytest.mark.parametrize("verb", ["get", "post"])
def test_one_click_unsubscribe_needs_no_login(client, user, subscribed, verb):
    resp = getattr(client, verb)(url(subscribed.unsubscribe_token))
    assert resp.status_code == 200
    assert resp.json() == {"race_result_email": False}
    subscribed.refresh_from_db()
    assert subscribed.race_result_email is False


def test_unsubscribe_is_idempotent(client, subscribed):
    for _ in range(3):
        assert client.post(url(subscribed.unsubscribe_token)).status_code == 200


def test_unknown_token_is_404(client, subscribed):
    assert client.get(url("nope")).status_code == 404
    assert client.post(url("nope")).status_code == 404
    subscribed.refresh_from_db()
    assert subscribed.race_result_email is True


def test_unsubscribe_only_affects_the_token_owner(client, subscribed):
    other = UserFactory()
    services.set_race_result_email(other, True)
    client.post(url(subscribed.unsubscribe_token))
    assert services.race_result_email_enabled(other) is True


def test_unsubscribe_ignores_session_and_csrf(subscribed):
    from rest_framework.test import APIClient

    c = APIClient(enforce_csrf_checks=True)
    c.force_login(UserFactory())
    assert c.post(url(subscribed.unsubscribe_token)).status_code == 200


def test_deleting_the_user_removes_the_preferences(user):
    services.get_pref(user)
    user.delete()
    assert NotificationPref.objects.count() == 0


def test_export_provider_data(user):
    assert services.export_user_data(user) == {"race_result_email": False}
    services.set_race_result_email(user, True)
    assert services.export_user_data(user) == {"race_result_email": True}


# --- Event handlers ---------------------------------------------------------------------------


@pytest.mark.parametrize("event_type", ["PredictionsScored", "SessionResultsFinalized"])
def test_handler_is_subscribed_on_startup(event_type):
    registry.clear()  # other tests wipe the registry; ready() must restore it
    apps.get_app_config("notifications").ready()
    assert handlers.handle_race_result in registry.handlers_for(event_type)


def test_subscribing_twice_does_not_duplicate_the_handler():
    registry.clear()
    handlers.register_handlers()
    handlers.register_handlers()
    assert registry.handlers_for("PredictionsScored").count(handlers.handle_race_result) == 1


@pytest.mark.parametrize(
    ("event_type", "key", "payload"),
    [
        ("PredictionsScored", "round:1", {"round_id": 1}),
        ("SessionResultsFinalized", "session:5", {"session_id": 5, "version": 1}),
    ],
)
def test_stub_handler_consumes_events_without_side_effects(
    event_type, key, payload, subscribed, mailoutbox
):
    registry.clear()
    handlers.register_handlers()
    publish(event_type, key=key, payload=payload)
    assert process_batch() == 1
    assert OutboxEvent.objects.get().status == OutboxEvent.Status.DONE
    assert mailoutbox == []

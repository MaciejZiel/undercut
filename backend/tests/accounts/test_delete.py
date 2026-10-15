import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from rest_framework.test import APIClient

from apps.accounts import services
from apps.accounts.models import Favorite
from apps.events.models import OutboxEvent
from apps.notifications.models import NotificationPref
from apps.notifications.services import get_pref
from tests.catalog.factories import DriverFactory

from .factories import UserFactory

pytestmark = pytest.mark.django_db

DELETE = "/api/v1/account/delete/"
User = get_user_model()


def test_requires_login(client):
    assert client.post(DELETE, {"display_name": "x"}, format="json").status_code == 403


@pytest.mark.parametrize("typed", ["wrong", "fan zero", "Fan", "x"])
def test_wrong_confirmation_deletes_nothing(auth_client, user, typed):
    user.display_name = "Fan Zero"
    user.save()
    resp = auth_client.post(DELETE, {"display_name": typed}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "confirmation_mismatch"
    assert User.objects.filter(pk=user.pk).exists()
    assert not OutboxEvent.objects.filter(type="UserDeleted").exists()


def test_confirmation_is_required(auth_client, user):
    assert auth_client.post(DELETE, {}, format="json").status_code == 400
    assert auth_client.post(DELETE, {"display_name": ""}, format="json").status_code == 400
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_is_immediate_and_removes_owned_data(auth_client, user):
    Favorite.objects.create(user=user, driver=DriverFactory())
    get_pref(user)
    resp = auth_client.post(DELETE, {"display_name": user.display_name}, format="json")
    assert resp.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()
    assert Favorite.objects.count() == 0
    assert NotificationPref.objects.count() == 0


def test_delete_publishes_user_deleted_with_the_user_id(auth_client, user):
    user_id = user.pk
    auth_client.post(DELETE, {"display_name": user.display_name}, format="json")
    event = OutboxEvent.objects.get(type="UserDeleted")
    assert event.key == f"user:{user_id}"
    assert event.payload == {"user_id": user_id}
    assert event.status == OutboxEvent.Status.PENDING


def test_event_and_deletion_commit_together(user, monkeypatch):
    """If the deletion fails after the event was written, the event rolls back with it."""

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(services, "_drop_sessions", boom)
    with pytest.raises(RuntimeError), transaction.atomic():
        services.delete_account(user, user.display_name)
    assert User.objects.filter(pk=user.pk).exists()
    assert not OutboxEvent.objects.filter(type="UserDeleted").exists()


def test_all_sessions_of_the_user_are_invalidated(user):
    first, second, bystander = APIClient(), APIClient(), APIClient()
    first.force_login(user)
    second.force_login(user)
    other = UserFactory()
    bystander.force_login(other)
    assert Session.objects.count() == 3

    resp = first.post(DELETE, {"display_name": user.display_name}, format="json")
    assert resp.status_code == 204
    assert second.get("/api/v1/auth/me/").json()["is_authenticated"] is False
    assert first.get("/api/v1/auth/me/").json()["is_authenticated"] is False
    assert Session.objects.count() == 1
    assert bystander.get("/api/v1/auth/me/").json()["is_authenticated"] is True


def test_deleted_user_cannot_log_in_again(client, user):
    from .conftest import ALLAUTH
    from .factories import PASSWORD

    email = user.email
    services.delete_account(user, user.display_name)
    resp = client.post(
        f"{ALLAUTH}/auth/login", {"email": email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 400


def test_display_name_can_be_reused_after_deletion(user):
    name = user.display_name
    services.delete_account(user, name)
    assert UserFactory(display_name=name).pk


def test_other_users_are_untouched(auth_client, user):
    bystander = UserFactory()
    Favorite.objects.create(user=bystander, driver=DriverFactory())
    auth_client.post(DELETE, {"display_name": user.display_name}, format="json")
    assert User.objects.filter(pk=bystander.pk).exists()
    assert Favorite.objects.filter(user=bystander).count() == 1

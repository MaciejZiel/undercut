import re
from datetime import datetime, timedelta
from urllib.parse import unquote

import pytest
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail

from .conftest import ALLAUTH
from .factories import PASSWORD, UserFactory

User = get_user_model()
pytestmark = pytest.mark.django_db

SIGNUP = f"{ALLAUTH}/auth/signup"


def signup(client, **overrides):
    data = {
        "email": "new@example.com",
        "password": "a-long-enough-passphrase",
        "display_name": "NewFan",
        **overrides,
    }
    return client.post(SIGNUP, data, format="json")


def mail_key():
    body = mail.outbox[-1].body
    # The key sits in the URL path, percent-encoded; the frontend route hands it back decoded.
    return unquote(re.search(r"/(?:verify-email|key)/([^\s/]+)", body).group(1))


def test_signup_creates_unverified_account_and_sends_confirmation(client):
    resp = signup(client)
    assert resp.status_code == 200, resp.content
    user = User.objects.get(email="new@example.com")
    assert user.display_name == "NewFan"
    assert user.email_verified is False
    assert user.can_predict is False
    assert len(mail.outbox) == 1
    assert "/account/verify-email/" in mail.outbox[0].body
    assert mail.outbox[0].from_email == settings.DEFAULT_FROM_EMAIL
    assert "NewFan" in mail.outbox[0].body
    assert mail.outbox[0].to == ["new@example.com"]


def test_unverified_user_is_logged_in_and_can_browse_but_not_predict(client):
    signup(client)
    me = client.get("/api/v1/auth/me/").json()
    assert me["is_authenticated"] is True
    assert me["user"]["email_verified"] is False
    assert me["user"]["can_predict"] is False


def test_confirming_the_email_link_sets_verified_and_can_predict(client):
    signup(client)
    resp = client.post(f"{ALLAUTH}/auth/email/verify", {"key": mail_key()}, format="json")
    assert resp.status_code == 200, resp.content
    user = User.objects.get(email="new@example.com")
    assert user.email_verified is True
    assert user.can_predict is True
    assert EmailAddress.objects.get(user=user).verified is True


def test_invalid_confirmation_key_is_rejected(client):
    signup(client)
    resp = client.post(f"{ALLAUTH}/auth/email/verify", {"key": "nope"}, format="json")
    assert resp.status_code == 400
    assert User.objects.get(email="new@example.com").email_verified is False


@pytest.mark.parametrize(
    "password", ["short1", "123456789012", "password1234"], ids=["short", "numeric", "common"]
)
def test_weak_passwords_are_rejected(client, password):
    resp = signup(client, password=password)
    assert resp.status_code == 400
    assert not User.objects.filter(email="new@example.com").exists()


def test_password_with_exactly_ten_characters_is_accepted(client):
    assert signup(client, password="xK9#mQ2$vL").status_code == 200


@pytest.mark.parametrize(
    "name",
    ["ab", "a" * 21, "bad<name>", "", "   ", "Admin", "deleted user"],
    ids=["short", "long", "chars", "empty", "blank", "reserved", "reserved-ci"],
)
def test_invalid_display_names_are_rejected(client, name):
    resp = signup(client, display_name=name)
    assert resp.status_code == 400
    assert not User.objects.filter(email="new@example.com").exists()


def test_display_name_length_boundaries(client):
    assert signup(client, email="a@example.com", display_name="abc").status_code == 200
    client.delete(f"{ALLAUTH}/auth/session")
    assert signup(client, email="b@example.com", display_name="x" * 20).status_code == 200


def test_display_name_is_unique_case_insensitively(client):
    UserFactory(display_name="Max")
    resp = signup(client, display_name="max")
    assert resp.status_code == 400
    assert not User.objects.filter(email="new@example.com").exists()


def test_display_name_is_required(client):
    data = {"email": "new@example.com", "password": "a-long-enough-passphrase"}
    assert client.post(SIGNUP, data, format="json").status_code == 400


def test_duplicate_email_does_not_create_a_second_account(client):
    UserFactory(email="taken@example.com")
    signup(client, email="taken@example.com", display_name="Other")
    assert User.objects.filter(email="taken@example.com").count() == 1


def test_login_and_logout(client):
    user = UserFactory()
    resp = client.post(
        f"{ALLAUTH}/auth/login", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me/").json()["is_authenticated"] is True
    client.delete(f"{ALLAUTH}/auth/session")
    assert client.get("/api/v1/auth/me/").json()["is_authenticated"] is False


# --- Password reset ---------------------------------------------------------------------------


def request_reset(client, email):
    return client.post(f"{ALLAUTH}/auth/password/request", {"email": email}, format="json")


def test_password_reset_flow(client):
    user = UserFactory()
    assert request_reset(client, user.email).status_code == 200
    assert "/account/password/reset/key/" in mail.outbox[0].body
    resp = client.post(
        f"{ALLAUTH}/auth/password/reset",
        {"key": mail_key(), "password": "brand-new-passphrase"},
        format="json",
    )
    assert resp.status_code in (200, 401), resp.content
    user.refresh_from_db()
    assert user.check_password("brand-new-passphrase")


def test_password_reset_for_unknown_email_sends_nothing_to_the_account(client):
    assert request_reset(client, "ghost@example.com").status_code == 200
    assert all("/password/reset/key/" not in m.body for m in mail.outbox)


def test_reset_timeout_is_one_hour():
    assert settings.PASSWORD_RESET_TIMEOUT == 3600


def _reset_key_status(client, key):
    return client.post(
        f"{ALLAUTH}/auth/password/reset",
        {"key": key, "password": "brand-new-passphrase"},
        format="json",
    ).status_code


@pytest.mark.parametrize(
    ("minutes", "valid"), [(59, True), (61, False)], ids=["inside-the-hour", "after-the-hour"]
)
def test_reset_link_expires_after_one_hour(client, monkeypatch, minutes, valid):
    user = UserFactory()
    request_reset(client, user.email)
    key = mail_key()
    later = datetime.now() + timedelta(minutes=minutes)
    monkeypatch.setattr(PasswordResetTokenGenerator, "_now", lambda self: later)
    status = _reset_key_status(client, key)
    user.refresh_from_db()
    assert user.check_password("brand-new-passphrase") is valid
    assert (status in (200, 401)) is valid

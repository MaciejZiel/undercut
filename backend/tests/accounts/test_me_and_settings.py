import pytest
from rest_framework.test import APIClient

from apps.notifications.models import NotificationPref

from .factories import UnverifiedUserFactory, UserFactory

pytestmark = pytest.mark.django_db

ME = "/api/v1/auth/me/"
SETTINGS = "/api/v1/account/settings/"


def test_csrf_endpoint_sets_the_cookie_and_returns_the_token(client):
    resp = client.get("/api/v1/auth/csrf/")
    assert resp.status_code == 200
    assert "csrftoken" in resp.cookies
    assert resp.json()["csrf_token"]


def test_csrf_is_enforced_for_session_authenticated_writes(user):
    c = APIClient(enforce_csrf_checks=True)
    c.force_login(user)
    assert c.patch(SETTINGS, {"theme": "dark"}, format="json").status_code == 403
    token = c.get("/api/v1/auth/csrf/").json()["csrf_token"]
    resp = c.patch(SETTINGS, {"theme": "dark"}, format="json", HTTP_X_CSRFTOKEN=token)
    assert resp.status_code == 200


def test_me_for_anonymous(client):
    assert client.get(ME).json() == {"is_authenticated": False, "user": None}


def test_me_for_a_verified_user(auth_client, user):
    data = auth_client.get(ME).json()
    assert data["is_authenticated"] is True
    assert data["user"] == {
        "id": user.pk,
        "display_name": user.display_name,
        "email": user.email,
        "email_verified": True,
        "can_predict": True,
        "timezone": "UTC",
        "theme": "system",
        "is_demo": False,
        "race_result_email": False,
    }
    assert "password" not in data["user"]


def test_me_for_an_unverified_user_cannot_predict():
    c = APIClient()
    c.force_login(UnverifiedUserFactory())
    user = c.get(ME).json()["user"]
    assert user["email_verified"] is False
    assert user["can_predict"] is False


def test_inactive_user_cannot_predict():
    assert UserFactory(is_active=False).can_predict is False


# --- PATCH settings ---------------------------------------------------------------------------


def test_settings_require_login(client):
    assert client.get(SETTINGS).status_code == 403
    assert client.patch(SETTINGS, {"theme": "dark"}, format="json").status_code == 403


def test_patch_updates_profile_settings(auth_client, user):
    resp = auth_client.patch(
        SETTINGS,
        {"display_name": "  New   Name ", "timezone": "Europe/Warsaw", "theme": "dark"},
        format="json",
    )
    assert resp.status_code == 200
    user.refresh_from_db()
    assert (user.display_name, user.timezone, user.theme) == ("New Name", "Europe/Warsaw", "dark")
    assert resp.json()["display_name"] == "New Name"


def test_patch_is_partial(auth_client, user):
    auth_client.patch(SETTINGS, {"theme": "light"}, format="json")
    user.refresh_from_db()
    assert user.theme == "light"
    assert user.timezone == "UTC"


@pytest.mark.parametrize("tz", ["Mars/Base", "../etc/passwd", "", "europe/warsaw"])
def test_invalid_timezone_is_rejected(auth_client, user, tz):
    resp = auth_client.patch(SETTINGS, {"timezone": tz}, format="json")
    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.timezone == "UTC"


def test_invalid_theme_is_rejected(auth_client):
    assert auth_client.patch(SETTINGS, {"theme": "neon"}, format="json").status_code == 400


@pytest.mark.parametrize("name", ["ab", "x" * 21, "bad<>name", "Admin"])
def test_invalid_display_name_is_rejected(auth_client, name):
    assert auth_client.patch(SETTINGS, {"display_name": name}, format="json").status_code == 400


def test_display_name_must_be_unique_ignoring_case(auth_client):
    UserFactory(display_name="Taken")
    resp = auth_client.patch(SETTINGS, {"display_name": "tAKEN"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "taken"


def test_keeping_the_same_display_name_is_allowed(auth_client, user):
    resp = auth_client.patch(SETTINGS, {"display_name": user.display_name}, format="json")
    assert resp.status_code == 200


def test_changing_only_the_case_of_own_name_is_allowed(auth_client, user):
    resp = auth_client.patch(SETTINGS, {"display_name": user.display_name.upper()}, format="json")
    assert resp.status_code == 200


def test_email_preference_is_off_by_default_and_can_be_toggled(auth_client, user):
    assert auth_client.get(SETTINGS).json()["race_result_email"] is False
    resp = auth_client.patch(SETTINGS, {"race_result_email": True}, format="json")
    assert resp.json()["race_result_email"] is True
    assert NotificationPref.objects.get(user=user).race_result_email is True
    resp = auth_client.patch(SETTINGS, {"race_result_email": False}, format="json")
    assert resp.json()["race_result_email"] is False


def test_unverified_user_may_change_settings():
    c = APIClient()
    c.force_login(UnverifiedUserFactory())
    assert c.patch(SETTINGS, {"theme": "dark"}, format="json").status_code == 200


def test_user_cannot_change_other_fields_through_settings(auth_client, user):
    auth_client.patch(
        SETTINGS, {"email_verified": False, "is_staff": True, "is_demo": True}, format="json"
    )
    user.refresh_from_db()
    assert (user.email_verified, user.is_staff, user.is_demo) == (True, False, False)

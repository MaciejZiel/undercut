import base64
import json
import time
import urllib.error
from urllib.parse import parse_qs, urlparse

import pytest
from allauth.account.models import EmailAddress

from apps.accounts import google
from apps.accounts.api.google_views import safe_next
from apps.accounts.models import GoogleIdentity, User

from .factories import UnverifiedUserFactory, UserFactory

START = "/api/v1/auth/google/start/"
CALLBACK = "/api/v1/auth/google/callback/"
STATUS = "/api/v1/auth/google/"
ME = "/api/v1/auth/me/"


@pytest.fixture(autouse=True)
def _google_settings(settings, db):
    settings.GOOGLE_CLIENT_ID = "client-id.apps.googleusercontent.com"
    settings.GOOGLE_CLIENT_SECRET = "client-secret"
    settings.GOOGLE_REDIRECT_URI = "https://example.test/api/v1/auth/google/callback/"


def token(flow_nonce: str, **overrides) -> str:
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "client-id.apps.googleusercontent.com",
        "exp": time.time() + 600,
        "nonce": flow_nonce,
        "sub": "sub-1",
        "email": "ada@example.com",
        "email_verified": True,
        "name": "Ada Lovelace",
    }
    claims.update(overrides)
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"e30.{body}.sig"


class Flow:
    """Drives one browser through start -> Google -> callback with Google's answer faked."""

    def __init__(self, client, monkeypatch):
        self.client = client
        self.monkeypatch = monkeypatch
        self.exchanged = []

    def start(self, **params):
        response = self.client.get(START, params)
        assert response.status_code == 302
        return response

    @property
    def flow(self):
        return self.client.session["google_oauth"]

    def callback(self, *, claims=None, state=None, code="the-code", **extra):
        flow = self.flow
        claims = claims or {}

        def fake_post(code_, verifier):
            self.exchanged.append((code_, verifier))
            return {"id_token": token(flow["nonce"], **claims)}

        self.monkeypatch.setattr(google, "_post_token", fake_post)
        query = {"state": state if state is not None else flow["state"], "code": code, **extra}
        return self.client.get(CALLBACK, query)

    def run(self, *, claims=None, **params):
        self.start(**params)
        return self.callback(claims=claims)


@pytest.fixture
def flow(client, monkeypatch):
    return Flow(client, monkeypatch)


def location(response) -> str:
    return response["Location"]


def me(client) -> dict:
    return client.get(ME).json()


# --- start ------------------------------------------------------------------------------------


def test_start_redirects_to_google_with_pkce_state_and_nonce(flow):
    response = flow.start(next="/predict")
    url = urlparse(location(response))
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == google.AUTH_URL
    assert query["client_id"] == "client-id.apps.googleusercontent.com"
    assert query["redirect_uri"] == "https://example.test/api/v1/auth/google/callback/"
    assert query["response_type"] == "code"
    assert query["scope"] == "openid email profile"
    assert query["code_challenge_method"] == "S256"
    saved = flow.flow
    assert query["state"] == saved["state"] and query["nonce"] == saved["nonce"]
    assert saved["next"] == "/predict"
    assert "verifier" not in query
    assert "no-store" in response["Cache-Control"]


def test_start_is_refused_when_not_configured(client, settings):
    settings.GOOGLE_CLIENT_SECRET = ""
    response = client.get(START)
    assert location(response) == "/login?google_error=disabled"
    assert "google_oauth" not in client.session


def test_link_mode_needs_a_signed_in_user(client):
    response = client.get(START, {"mode": "link"})
    assert location(response) == "/login?google_error=unauthenticated"


@pytest.mark.parametrize(
    "value",
    ["https://evil.test", "//evil.test", "/\\evil.test", "evil", "", None, "/a\nb", "/x\r"],
)
def test_safe_next_rejects_anything_but_a_local_path(value):
    assert safe_next(value) == "/"


def test_safe_next_keeps_local_paths():
    assert safe_next("/seasons/2024/5?tab=replay") == "/seasons/2024/5?tab=replay"


# --- sign up and sign in ----------------------------------------------------------------------


def test_new_google_user_is_created_verified_and_logged_in(db, flow, client):
    response = flow.run(next="/predict")
    assert location(response) == "/predict"
    user = User.objects.get(email="ada@example.com")
    assert user.email_verified and user.can_predict
    assert not user.has_usable_password()
    assert user.display_name == "Ada Lovelace"
    assert user.username.startswith("g_")
    address = EmailAddress.objects.get(user=user)
    assert address.primary and address.verified
    assert GoogleIdentity.objects.get(user=user).sub == "sub-1"
    assert me(client)["user"]["email"] == "ada@example.com"
    assert flow.exchanged and flow.exchanged[0][0] == "the-code"


def test_display_name_is_made_unique_and_valid(db, flow):
    UserFactory(display_name="Ada Lovelace")
    flow.run()
    created = User.objects.get(email="ada@example.com")
    assert created.display_name != "Ada Lovelace"
    assert created.display_name.startswith("Ada Lovelace")
    assert 3 <= len(created.display_name) <= 20


def test_unusable_profile_name_falls_back_to_the_email(db, flow):
    flow.run(claims={"name": "💥", "email": "grace.hopper@example.com"})
    assert User.objects.get(email="grace.hopper@example.com").display_name == "grace.hopper"


def test_known_sub_logs_in_even_after_the_email_changed(db, flow, client):
    flow.run()
    client.cookies.clear()
    response = flow.run(claims={"email": "new-address@example.com"})
    assert location(response) == "/"
    assert User.objects.count() == 1
    assert me(client)["user"]["email"] == "ada@example.com"


def test_existing_verified_account_is_linked_not_duplicated(db, flow, client):
    user = UserFactory(email="ada@example.com")
    flow.run()
    assert User.objects.count() == 1
    assert GoogleIdentity.objects.get().user == user
    assert me(client)["user"]["id"] == user.id


def test_existing_unverified_account_is_never_taken_over(db, flow, client):
    UnverifiedUserFactory(email="ada@example.com")
    response = flow.run()
    assert location(response) == "/login?google_error=email_unverified_account"
    assert not GoogleIdentity.objects.exists()
    assert me(client)["is_authenticated"] is False


def test_email_only_on_the_user_row_blocks_signup(db, flow, client):
    User.objects.create(username="legacy", email="ada@example.com")
    response = flow.run()
    assert location(response) == "/login?google_error=email_taken"
    assert User.objects.count() == 1


def test_inactive_and_demo_accounts_cannot_sign_in(db, flow, client):
    user = UserFactory(email="ada@example.com", is_active=False)
    assert location(flow.run()) == "/login?google_error=account_unavailable"
    user.is_active, user.is_demo = True, True
    user.save()
    assert location(flow.run()) == "/login?google_error=account_unavailable"
    assert me(client)["is_authenticated"] is False


def test_signing_in_rotates_the_session_key(db, flow, client):
    client.get("/api/v1/auth/csrf/")
    flow.start()
    before = client.session.session_key
    flow.callback()
    assert client.session.session_key != before


# --- failures ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("claims", "code"),
    [
        ({"nonce": "other"}, "invalid_token"),
        ({"aud": "someone-else"}, "invalid_token"),
        ({"iss": "https://evil.test"}, "invalid_token"),
        ({"exp": time.time() - 3600}, "invalid_token"),
        ({"sub": ""}, "invalid_token"),
        ({"email_verified": False}, "email_unverified"),
        ({"email_verified": "yes"}, "email_unverified"),
        ({"email": None}, "email_missing"),
    ],
)
def test_bad_id_tokens_are_rejected(db, flow, client, claims, code):
    response = flow.run(claims=claims)
    assert location(response) == f"/login?google_error={code}"
    assert not User.objects.exists()
    assert me(client)["is_authenticated"] is False


def test_audience_may_be_a_list(db, flow):
    response = flow.run(claims={"aud": ["x", "client-id.apps.googleusercontent.com"]})
    assert location(response) == "/"


def test_wrong_state_is_rejected(db, flow):
    flow.start()
    response = flow.callback(state="forged")
    assert location(response) == "/login?google_error=invalid_state"
    assert not flow.exchanged


def test_callback_without_a_started_flow_is_rejected(db, client):
    response = client.get(CALLBACK, {"state": "x", "code": "y"})
    assert location(response) == "/login?google_error=invalid_state"


def test_a_flow_can_only_be_used_once(db, flow):
    flow.start()
    stale = flow.flow["state"]
    assert location(flow.callback()) == "/"
    assert location(flow.client.get(CALLBACK, {"state": stale, "code": "again"})).endswith(
        "google_error=invalid_state"
    )


def test_expired_flow_is_rejected(db, flow, monkeypatch):
    flow.start()
    session = flow.client.session
    session["google_oauth"]["started"] -= google.FLOW_TTL_SECONDS + 5
    session.save()
    assert location(flow.callback()).endswith("google_error=expired")


def test_user_cancelling_is_reported(db, flow):
    flow.start()
    response = flow.client.get(CALLBACK, {"error": "access_denied", "state": flow.flow["state"]})
    assert location(response) == "/login?google_error=cancelled"


def test_google_being_unreachable_is_reported(db, client, monkeypatch):
    client.get(START)

    def boom(*args, **kwargs):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(google.urllib.request, "urlopen", boom)
    state = client.session["google_oauth"]["state"]
    response = client.get(CALLBACK, {"state": state, "code": "c"})
    assert location(response) == "/login?google_error=unavailable"


def test_google_rejecting_the_code_is_reported(db, client, monkeypatch):
    client.get(START)

    def reject(*args, **kwargs):
        raise urllib.error.HTTPError("u", 400, "bad", {}, None)

    monkeypatch.setattr(google.urllib.request, "urlopen", reject)
    state = client.session["google_oauth"]["state"]
    response = client.get(CALLBACK, {"state": state, "code": "c"})
    assert location(response) == "/login?google_error=exchange_failed"


# --- linking and unlinking --------------------------------------------------------------------


def test_signed_in_user_can_link_google(db, auth_client, user, monkeypatch):
    f = Flow(auth_client, monkeypatch)
    f.start(mode="link")
    response = f.callback(claims={"email": "other@example.com"})
    assert location(response) == "/settings?google=linked"
    assert GoogleIdentity.objects.get(user=user).email == "other@example.com"


def test_google_account_of_someone_else_cannot_be_linked(db, auth_client, monkeypatch):
    UserFactory().google_identity = GoogleIdentity.objects.create(
        user=UserFactory(), sub="sub-1", email="x@example.com"
    )
    f = Flow(auth_client, monkeypatch)
    f.start(mode="link")
    assert location(f.callback()) == "/settings?google_error=google_in_use"


def test_link_fails_when_the_session_user_changed(db, auth_client, monkeypatch):
    f = Flow(auth_client, monkeypatch)
    f.start(mode="link")
    session = auth_client.session
    session["google_oauth"]["user_id"] = UserFactory().pk  # as if another person's flow was reused
    session.save()
    assert location(f.callback()).endswith("google_error=unauthenticated")
    assert not GoogleIdentity.objects.exists()


def test_unlink_needs_a_password(db, auth_client, user):
    GoogleIdentity.objects.create(user=user, sub="s", email="a@example.com")
    assert auth_client.delete(STATUS).status_code == 204
    assert not GoogleIdentity.objects.exists()


def test_unlink_is_refused_without_a_password(db, flow, client):
    flow.run()
    response = client.delete(STATUS)
    assert response.status_code == 409
    assert response.json()["code"] == "last_login_method"
    assert GoogleIdentity.objects.exists()


def test_unlink_needs_a_session(db, client):
    assert client.delete(STATUS).status_code in (401, 403)


# --- status and cleanup -----------------------------------------------------------------------


def test_status_for_anonymous_and_linked_users(db, client, auth_client, user):
    assert client.get(STATUS).json() == {
        "enabled": True,
        "linked": False,
        "email": None,
        "has_password": False,
    }
    GoogleIdentity.objects.create(user=user, sub="s", email="a@example.com")
    assert auth_client.get(STATUS).json() == {
        "enabled": True,
        "linked": True,
        "email": "a@example.com",
        "has_password": True,
    }


def test_status_reports_disabled_without_keys(client, settings):
    settings.GOOGLE_CLIENT_ID = ""
    assert client.get(STATUS).json()["enabled"] is False


def test_identity_is_deleted_with_the_user(db, user):
    GoogleIdentity.objects.create(user=user, sub="s", email="a@example.com")
    user.delete()
    assert not GoogleIdentity.objects.exists()


def test_tokens_and_secret_never_reach_the_log(db, flow, caplog):
    with caplog.at_level("DEBUG"):
        flow.run(claims={"nonce": "wrong"})
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "client-secret" not in text and "the-code" not in text

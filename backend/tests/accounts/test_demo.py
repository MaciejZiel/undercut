import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts import handlers, services
from apps.accounts.models import Favorite
from apps.events import registry
from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.worker import process_batch
from tests.catalog.factories import ConstructorFactory, DriverFactory

from .conftest import ALLAUTH
from .factories import UserFactory

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def catalog():
    DriverFactory(given_name="Max", family_name="Verstappen", slug="max-verstappen")
    DriverFactory(given_name="Lando", family_name="Norris", slug="norris")
    DriverFactory(given_name="Someone", family_name="Else", slug="someone-else")
    ConstructorFactory(slug="red-bull")
    ConstructorFactory(slug="mclaren")


@pytest.fixture
def demo(catalog):
    call_command("seed_demo_user")
    return services.get_demo_user()


@pytest.fixture
def demo_client(demo):
    c = APIClient()
    c.force_login(demo)
    return c


def favorites(user):
    return sorted(
        (f.driver.slug if f.driver_id else f.constructor.slug)
        for f in Favorite.objects.filter(user=user).select_related("driver", "constructor")
    )


# --- Seeding ----------------------------------------------------------------------------------


def test_seed_creates_a_locked_demo_user(demo):
    assert demo.is_demo
    assert demo.email_verified and demo.can_predict
    assert not demo.has_usable_password()
    assert demo.email == ""
    assert not (demo.is_staff or demo.is_superuser)
    assert favorites(demo) == ["max-verstappen", "mclaren", "norris", "red-bull"]


def test_seed_is_idempotent(demo):
    call_command("seed_demo_user")
    call_command("seed_demo_user")
    assert User.objects.filter(is_demo=True).count() == 1
    assert Favorite.objects.filter(user=demo).count() == 4


def test_seed_repairs_a_tampered_account(demo):
    demo.is_staff = True
    demo.set_password("hunter2hunter2")
    demo.save()
    call_command("seed_demo_user")
    demo.refresh_from_db()
    assert not demo.is_staff
    assert not demo.has_usable_password()


def test_missing_catalog_entries_are_skipped():
    call_command("seed_demo_user")
    assert favorites(services.get_demo_user()) == []


# --- Demo login -------------------------------------------------------------------------------


def test_demo_login_endpoint(client, demo):
    resp = client.post("/api/v1/auth/demo/")
    assert resp.status_code == 200
    assert resp.json()["user"]["is_demo"] is True
    assert client.get("/api/v1/auth/me/").json()["user"]["id"] == demo.pk


def test_demo_login_without_a_demo_user_is_404(client):
    assert client.post("/api/v1/auth/demo/").status_code == 404


def test_demo_login_enforces_csrf(demo):
    c = APIClient(enforce_csrf_checks=True)
    assert c.post("/api/v1/auth/demo/").status_code == 403
    token = c.get("/api/v1/auth/csrf/").json()["csrf_token"]
    assert c.post("/api/v1/auth/demo/", HTTP_X_CSRFTOKEN=token).status_code == 200


def test_demo_cannot_log_in_with_a_password(client, demo):
    resp = client.post(
        f"{ALLAUTH}/auth/login", {"email": "", "password": "anything-at-all"}, format="json"
    )
    assert resp.status_code == 400


# --- Server-side restrictions -----------------------------------------------------------------


def test_demo_cannot_delete_itself(demo_client, demo):
    resp = demo_client.post(
        "/api/v1/account/delete/", {"display_name": demo.display_name}, format="json"
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "demo_locked"
    assert User.objects.filter(pk=demo.pk).exists()
    assert not OutboxEvent.objects.filter(type="UserDeleted").exists()


def test_demo_cannot_rename_itself(demo_client, demo):
    resp = demo_client.patch("/api/v1/account/settings/", {"display_name": "Hacked"}, format="json")
    assert resp.status_code == 403
    demo.refresh_from_db()
    assert demo.display_name == "Demo"


def test_demo_may_change_theme_and_timezone(demo_client):
    resp = demo_client.patch(
        "/api/v1/account/settings/", {"theme": "dark", "timezone": "Europe/Warsaw"}, format="json"
    )
    assert resp.status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/account/email", {"email": "evil@example.com"}),
        ("put", "/account/email", {"email": "evil@example.com"}),
        ("delete", "/account/email", {"email": "evil@example.com"}),
        ("patch", "/account/email", {"email": "evil@example.com"}),
        ("post", "/account/password/change", {"new_password": "a-long-new-password"}),
        ("post", "/auth/reauthenticate", {"password": "x"}),
    ],
)
def test_demo_cannot_change_email_or_password(demo_client, demo, method, path, body):
    resp = getattr(demo_client, method)(f"{ALLAUTH}{path}", body, format="json")
    assert resp.status_code == 403
    assert resp.json()["code"] == "demo_locked"
    demo.refresh_from_db()
    assert not demo.has_usable_password()
    assert demo.email == ""


def test_regular_users_are_not_blocked_by_the_demo_lock(auth_client):
    resp = auth_client.post(
        f"{ALLAUTH}/account/email", {"email": "second@example.com"}, format="json"
    )
    assert resp.status_code != 403 or resp.json().get("code") != "demo_locked"


def test_demo_can_still_read_account_endpoints(demo_client):
    assert demo_client.get(f"{ALLAUTH}/account/email").status_code in (200, 401)
    assert demo_client.get("/api/v1/auth/me/").status_code == 200


def test_demo_can_edit_favorites(demo_client):
    assert demo_client.delete("/api/v1/favorites/drivers/max-verstappen/").status_code == 200


# --- Nightly reset ----------------------------------------------------------------------------


def test_reset_restores_the_starting_favorites(demo):
    Favorite.objects.filter(user=demo).delete()
    Favorite.objects.create(user=demo, driver=services_driver("someone-else"))
    services.reset_demo_account()
    assert favorites(demo) == ["max-verstappen", "mclaren", "norris", "red-bull"]


def services_driver(slug):
    return Favorite._meta.get_field("driver").related_model.objects.get(slug=slug)


def test_reset_leaves_other_users_alone(demo):
    other = UserFactory()
    Favorite.objects.create(user=other, driver=services_driver("someone-else"))
    services.reset_demo_account()
    assert favorites(other) == ["someone-else"]


def test_reset_without_a_demo_user_is_a_noop(db):
    services.reset_demo_account()


def test_demo_reset_due_event_is_handled_through_the_outbox(demo):
    registry.clear()
    handlers.register_handlers()
    Favorite.objects.filter(user=demo).delete()
    publish("DemoResetDue", key="demo-reset", payload={"slot": "2026-10-16T02:00:00Z"})
    assert process_batch() == 1
    assert len(favorites(demo)) == 4
    # At-least-once delivery: handling the same event twice yields the same state.
    handlers.handle_demo_reset_due(OutboxEvent.objects.get(type="DemoResetDue"))
    assert len(favorites(demo)) == 4


def test_accounts_subscribes_to_demo_reset_due_on_startup():
    from django.apps import apps

    registry.clear()
    apps.get_app_config("accounts").ready()
    assert handlers.handle_demo_reset_due in registry.handlers_for("DemoResetDue")

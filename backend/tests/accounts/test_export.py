import json

import pytest

from apps.accounts import exports
from apps.accounts.models import Favorite
from apps.notifications.services import set_race_result_email
from tests.catalog.factories import ConstructorFactory, DriverFactory

from .factories import UserFactory

pytestmark = pytest.mark.django_db

EXPORT = "/api/v1/account/export/"


def test_export_requires_login(client):
    assert client.get(EXPORT).status_code == 403


def test_export_contains_profile_favorites_and_notification_preferences(auth_client, user):
    Favorite.objects.create(user=user, driver=DriverFactory(slug="max-verstappen"))
    Favorite.objects.create(user=user, constructor=ConstructorFactory(slug="red-bull"))
    set_race_result_email(user, True)
    resp = auth_client.get(EXPORT)
    assert resp.status_code == 200
    assert "attachment" in resp["Content-Disposition"]
    data = json.loads(resp.content)
    assert data["profile"]["email"] == user.email
    assert data["profile"]["display_name"] == user.display_name
    assert "password" not in data["profile"]
    assert data["favorites"] == {"drivers": ["max-verstappen"], "constructors": ["red-bull"]}
    assert data["notifications"] == {"race_result_email": True}
    assert "exported_at" in data


def test_export_never_includes_another_users_data(auth_client, user):
    other = UserFactory()
    Favorite.objects.create(user=other, driver=DriverFactory(slug="someone-else"))
    data = json.loads(auth_client.get(EXPORT).content)
    assert data["favorites"]["drivers"] == []
    assert other.email not in json.dumps(data)


def test_registered_provider_is_called_with_the_user(auth_client, user, isolated_exports):
    exports.register_export_provider("predictions", lambda u: [{"owner": u.pk}])
    data = json.loads(auth_client.get(EXPORT).content)
    assert data["predictions"] == [{"owner": user.pk}]


def test_registering_a_name_again_replaces_the_provider(user, isolated_exports):
    exports.register_export_provider("x", lambda u: 1)
    exports.register_export_provider("x", lambda u: 2)
    assert exports.collect(user)["x"] == 2
    assert exports.provider_names().count("x") == 1


@pytest.mark.parametrize("name", ["profile", "favorites", "exported_at"])
def test_reserved_names_are_refused(name):
    with pytest.raises(ValueError):
        exports.register_export_provider(name, lambda u: None)


def test_invalid_registration_is_refused():
    with pytest.raises(ValueError):
        exports.register_export_provider("", lambda u: None)
    with pytest.raises(ValueError):
        exports.register_export_provider("x", "not callable")


def test_failing_provider_fails_the_export_instead_of_truncating_it(auth_client, isolated_exports):
    def boom(user):
        raise RuntimeError("nope")

    exports.register_export_provider("broken", boom)
    auth_client.raise_request_exception = False
    assert auth_client.get(EXPORT).status_code == 500


def test_other_modules_registered_themselves_on_startup():
    # notifications registers in AppConfig.ready(); the predictions module does the same.
    assert "notifications" in exports.provider_names()

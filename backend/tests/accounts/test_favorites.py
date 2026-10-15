import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.accounts.models import Favorite
from tests.catalog.factories import ConstructorFactory, DriverFactory

from .factories import UserFactory

pytestmark = pytest.mark.django_db

LIST = "/api/v1/favorites/"


def drv(slug):
    return f"/api/v1/favorites/drivers/{slug}/"


def con(slug):
    return f"/api/v1/favorites/constructors/{slug}/"


@pytest.fixture
def driver():
    return DriverFactory(given_name="Max", family_name="Verstappen", slug="max-verstappen")


@pytest.fixture
def constructor():
    return ConstructorFactory(slug="red-bull", name="Red Bull")


def test_all_endpoints_require_login(client, driver, constructor):
    assert client.get(LIST).status_code == 403
    assert client.put(drv(driver.slug)).status_code == 403
    assert client.delete(drv(driver.slug)).status_code == 403
    assert client.put(con(constructor.slug)).status_code == 403
    assert client.delete(con(constructor.slug)).status_code == 403
    assert Favorite.objects.count() == 0


def test_add_list_and_remove_driver(auth_client, driver):
    assert auth_client.put(drv(driver.slug)).json() == {"favorite": True}
    data = auth_client.get(LIST).json()
    assert [d["slug"] for d in data["drivers"]] == ["max-verstappen"]
    assert data["drivers"][0]["name"] == "Max Verstappen"
    assert data["constructors"] == []
    assert data["limits"] == {"drivers": 10, "constructors": 5}
    assert auth_client.delete(drv(driver.slug)).json() == {"favorite": False}
    assert auth_client.get(LIST).json()["drivers"] == []


def test_add_and_remove_constructor(auth_client, constructor):
    assert auth_client.put(con(constructor.slug)).status_code == 200
    assert auth_client.get(LIST).json()["constructors"] == [
        {"slug": "red-bull", "name": "Red Bull"}
    ]
    assert auth_client.delete(con(constructor.slug)).status_code == 200
    assert Favorite.objects.count() == 0


def test_add_is_idempotent(auth_client, driver):
    for _ in range(3):
        assert auth_client.put(drv(driver.slug)).status_code == 200
    assert Favorite.objects.count() == 1


def test_remove_is_idempotent(auth_client, driver):
    assert auth_client.delete(drv(driver.slug)).status_code == 200
    assert auth_client.delete(drv("no-such-driver")).status_code == 200


def test_unknown_target_is_404(auth_client):
    assert auth_client.put(drv("nobody")).status_code == 404
    assert auth_client.put(con("nobody")).status_code == 404


def test_driver_limit_is_ten(auth_client):
    drivers = DriverFactory.create_batch(11)
    for d in drivers[:10]:
        assert auth_client.put(drv(d.slug)).status_code == 200
    resp = auth_client.put(drv(drivers[10].slug))
    assert resp.status_code == 409
    assert resp.json()["code"] == "favorites_limit"
    assert Favorite.objects.filter(driver__isnull=False).count() == 10


def test_constructor_limit_is_five(auth_client):
    teams = ConstructorFactory.create_batch(6)
    for t in teams[:5]:
        assert auth_client.put(con(t.slug)).status_code == 200
    assert auth_client.put(con(teams[5].slug)).status_code == 409


def test_limits_are_independent_per_kind(auth_client):
    for d in DriverFactory.create_batch(10):
        auth_client.put(drv(d.slug))
    assert auth_client.put(con(ConstructorFactory().slug)).status_code == 200


def test_readding_an_existing_favorite_at_the_limit_still_succeeds(auth_client):
    drivers = DriverFactory.create_batch(10)
    for d in drivers:
        auth_client.put(drv(d.slug))
    assert auth_client.put(drv(drivers[0].slug)).status_code == 200


def test_removing_frees_a_slot(auth_client):
    drivers = DriverFactory.create_batch(11)
    for d in drivers[:10]:
        auth_client.put(drv(d.slug))
    auth_client.delete(drv(drivers[0].slug))
    assert auth_client.put(drv(drivers[10].slug)).status_code == 200


def test_limits_are_per_user(auth_client):
    drivers = DriverFactory.create_batch(10)
    for d in drivers:
        auth_client.put(drv(d.slug))
    other = APIClient()
    other.force_login(UserFactory())
    assert other.put(drv(drivers[0].slug)).status_code == 200


def test_users_only_see_and_change_their_own_favorites(auth_client, driver):
    other_user = UserFactory()
    other = APIClient()
    other.force_login(other_user)
    other.put(drv(driver.slug))
    assert auth_client.get(LIST).json()["drivers"] == []
    auth_client.delete(drv(driver.slug))  # does not touch the other user's row
    assert Favorite.objects.filter(user=other_user).count() == 1


def test_favorites_work_for_unverified_accounts(driver):
    from .factories import UnverifiedUserFactory

    c = APIClient()
    c.force_login(UnverifiedUserFactory())
    assert c.put(drv(driver.slug)).status_code == 200


# --- Database constraints ---------------------------------------------------------------------


def test_db_requires_exactly_one_target(user, driver, constructor):
    for kwargs in ({}, {"driver": driver, "constructor": constructor}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=user, **kwargs)


def test_db_rejects_duplicates(user, driver, constructor):
    Favorite.objects.create(user=user, driver=driver)
    Favorite.objects.create(user=user, constructor=constructor)
    with pytest.raises(IntegrityError), transaction.atomic():
        Favorite.objects.create(user=user, driver=driver)
    with pytest.raises(IntegrityError), transaction.atomic():
        Favorite.objects.create(user=user, constructor=constructor)


def test_the_same_target_may_be_favorited_by_different_users(driver):
    a, b = UserFactory.create_batch(2)
    Favorite.objects.create(user=a, driver=driver)
    Favorite.objects.create(user=b, driver=driver)

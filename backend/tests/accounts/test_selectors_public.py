import pytest

from apps.accounts import selectors_public as public
from apps.accounts.models import Favorite
from apps.notifications import services as notifications
from tests.catalog.factories import ConstructorFactory, DriverFactory

from .factories import UnverifiedUserFactory, UserFactory

pytestmark = pytest.mark.django_db


def opted_in(factory=UserFactory, **kwargs):
    user = factory(**kwargs)
    notifications.set_race_result_email(user, True)
    return user


def test_recipients_are_opted_in_verified_real_active_users():
    good = opted_in(email="good@example.com", display_name="Good")
    opted_in(UnverifiedUserFactory)
    opted_in(is_demo=True)
    inactive = opted_in()
    inactive.is_active = False
    inactive.save()
    UserFactory()  # never opted in
    unsubscribed = opted_in()
    notifications.unsubscribe(notifications.get_pref(unsubscribed).unsubscribe_token)

    found = list(public.iter_race_email_recipients())

    assert [(r.user_id, r.email, r.display_name) for r in found] == [
        (good.pk, "good@example.com", "Good")
    ]
    assert public.get_race_email_recipient(good.pk) is not None
    assert public.get_race_email_recipient(unsubscribed.pk) is None


def test_recipients_are_read_in_chunks(monkeypatch):
    monkeypatch.setattr(public, "CHUNK", 2)
    users = [opted_in() for _ in range(5)]
    assert [r.user_id for r in public.iter_race_email_recipients()] == [u.pk for u in users]


def test_favorite_ids():
    user = UserFactory()
    d1, d2 = DriverFactory(), DriverFactory()
    c = ConstructorFactory()
    Favorite.objects.create(user=user, driver=d1)
    Favorite.objects.create(user=user, constructor=c)
    Favorite.objects.create(user=user, driver=d2)
    assert public.favorite_ids(user.pk) == ([d1.pk, d2.pk], [c.pk])

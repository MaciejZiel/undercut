import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import CanPredict

from .factories import UnverifiedUserFactory, UserFactory

pytestmark = pytest.mark.django_db


def allowed(user):
    request = APIRequestFactory().get("/")
    request.user = user or AnonymousUser()
    return CanPredict().has_permission(request, None)


def test_anonymous_is_denied():
    assert allowed(None) is False


def test_unverified_is_denied():
    assert allowed(UnverifiedUserFactory()) is False


def test_inactive_is_denied():
    assert allowed(UserFactory(is_active=False)) is False


def test_verified_is_allowed():
    assert allowed(UserFactory()) is True

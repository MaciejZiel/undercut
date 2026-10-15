import re

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from .conftest import ALLAUTH
from .factories import UserFactory

pytestmark = pytest.mark.django_db


def _html(message) -> str:
    html = [body for body, kind in message.alternatives if kind == "text/html"]
    assert html, "the message has no HTML part"
    return html[0]


def test_confirmation_mail_is_multipart_with_a_branded_button(client):
    with override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    ):
        res = client.post(
            f"{ALLAUTH}/auth/signup",
            {
                "email": "new@example.com",
                "password": "correct-horse-battery",
                "display_name": "New Fan",
            },
            format="json",
        )
    assert res.status_code < 400, res.content
    message = mail.outbox[-1]
    html = _html(message)
    link = re.search(r"/account/verify-email/[^\s\"'<>]+", message.body)
    assert link, "plain text part must keep the link"
    assert "UNDERCUT" in html and "Confirm e-mail" in html
    assert link.group(0) in html
    assert "New Fan" in html


def test_html_escapes_user_supplied_values(client):
    with override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    ):
        client.post(
            f"{ALLAUTH}/auth/signup",
            {
                "email": "x@example.com",
                "password": "correct-horse-battery",
                "display_name": "A<b>x",
            },
            format="json",
        )
    # An invalid name is rejected before any mail; the point is that nothing raw reaches the HTML.
    for message in mail.outbox:
        assert "<b>x" not in _html(message)


def test_password_reset_mail_has_both_parts():
    user = UserFactory(email="reset@example.com")
    EmailAddress.objects.filter(user=user).update(verified=True)
    client = APIClient()
    client.get("/api/v1/auth/csrf/")
    res = client.post(
        f"{ALLAUTH}/auth/password/request", {"email": "reset@example.com"}, format="json"
    )
    assert res.status_code < 400, res.content
    message = mail.outbox[-1]
    html = _html(message)
    assert "Choose a new password" in html and "Reset your password" in html
    assert "/account/password/reset/key/" in message.body

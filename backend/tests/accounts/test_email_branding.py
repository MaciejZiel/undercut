from types import SimpleNamespace

from django.template.loader import render_to_string

from apps.accounts.models import User


def test_account_e_mails_are_branded_with_the_site_name_not_the_host():
    site = SimpleNamespace(
        name="undercut.maciejzielinski.dev", domain="undercut.maciejzielinski.dev"
    )
    body = render_to_string(
        "account/email/email_confirmation_message.txt",
        {
            "current_site": site,
            "user": User(username="tester", display_name="Tester"),
            "activate_url": "https://x/y",
        },
    )
    assert body.startswith("Hello from Undercut!")
    assert "Thank you for using Undercut." in body
    assert "https://x/y" in body

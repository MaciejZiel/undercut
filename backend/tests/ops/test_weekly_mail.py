import pytest
from django.core import mail

from apps.ops import handlers

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    settings.ALERT_EMAIL_TO = ["owner@example.com"]


def test_report_lists_problems(healthy_heartbeats, make_event):
    from apps.events.models import OutboxEvent

    make_event(status=OutboxEvent.Status.DEAD)
    subject, body = handlers.build_report()
    assert "needs attention" in subject
    assert "outbox_dead" in body and "1 dead" in body


def test_healthy_report_and_mail(healthy_heartbeats):
    handlers.on_weekly_health_due(object())
    (message,) = mail.outbox
    assert message.to == ["owner@example.com"]
    assert message.subject == "[Undercut] Weekly check"
    assert "all good" in message.body


def test_no_recipient_sends_nothing(settings):
    settings.ALERT_EMAIL_TO = []
    handlers.on_weekly_health_due(object())
    assert mail.outbox == []


def test_a_mail_failure_is_raised_for_the_outbox_to_retry(healthy_heartbeats, monkeypatch):
    def boom(self, *args, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", boom)
    with pytest.raises(OSError):
        handlers.on_weekly_health_due(object())

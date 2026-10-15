import datetime as dt

import pytest
from django.core import mail
from django.utils import timezone

from apps.ingestion import alerts, failures
from apps.ingestion.models import SyncRun

pytestmark = pytest.mark.django_db

LOCMEM = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}


@pytest.fixture(autouse=True)
def _mail(settings):
    settings.MAILERS = LOCMEM
    settings.ALERT_EMAIL_TO = ["owner@example.com"]


def run(status, *, job="session-results", source="jolpica-api", age_minutes=0, error="boom"):
    # started_at is auto_now_add (creation order decides); finished_at carries the age.
    started = timezone.now() - dt.timedelta(minutes=age_minutes)
    return SyncRun.objects.create(
        source=source,
        job=job,
        status=status,
        started_at=started,
        finished_at=started,
        errors=[{"error": error}] if status == SyncRun.Status.FAILED else [],
    )


def test_counts_failures_since_the_last_good_run():
    run(SyncRun.Status.FAILED, age_minutes=50)
    run(SyncRun.Status.SUCCESS, age_minutes=40)
    run(SyncRun.Status.FAILED, age_minutes=30)
    run(SyncRun.Status.RUNNING, age_minutes=20)
    run(SyncRun.Status.FAILED, age_minutes=10)
    assert failures.consecutive_failures("jolpica-api", "session-results") == 2


@pytest.mark.parametrize(
    ("n", "expected"), [(1, False), (2, True), (3, False), (10, True), (20, True), (11, False)]
)
def test_alert_schedule(n, expected):
    assert alerts.should_alert(n) is expected


def test_no_mail_for_a_single_failure():
    run(SyncRun.Status.FAILED)
    assert alerts.notify(SyncRun.objects.get()) is False
    assert mail.outbox == []


def test_mail_on_the_second_failure_in_a_row_only_once():
    first = run(SyncRun.Status.FAILED, age_minutes=60)
    assert alerts.notify(first) is False
    second = run(SyncRun.Status.FAILED, age_minutes=0, error="HTTP 503 from upstream")
    assert alerts.notify(second) is True
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["owner@example.com"]
    assert "session-results" in message.subject and "2 in a row" in message.subject
    assert "HTTP 503 from upstream" in message.body
    second.refresh_from_db()
    assert second.scope["alerted"] is True
    assert alerts.notify(second) is False  # saving the run again must not send it twice
    assert len(mail.outbox) == 1


def test_no_recipients_means_no_mail(settings):
    settings.ALERT_EMAIL_TO = []
    run(SyncRun.Status.FAILED, age_minutes=60)
    assert alerts.notify(run(SyncRun.Status.FAILED)) is False
    assert mail.outbox == []


def test_a_broken_mail_server_does_not_raise(settings, monkeypatch):
    run(SyncRun.Status.FAILED, age_minutes=60)
    last = run(SyncRun.Status.FAILED)

    def boom(self, *args, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", boom)
    assert alerts.notify(last) is False
    last.refresh_from_db()
    assert "alerted" not in last.scope


def test_saving_a_failed_run_sends_the_alert(django_capture_on_commit_callbacks):
    run(SyncRun.Status.FAILED, age_minutes=60)
    with django_capture_on_commit_callbacks(execute=True):
        SyncRun.objects.create(
            source="jolpica-api", job="session-results", status=SyncRun.Status.FAILED
        )
    assert len(mail.outbox) == 1


def test_failing_jobs_lists_only_recent_repeated_failures():
    run(SyncRun.Status.FAILED, job="a", age_minutes=20)
    run(SyncRun.Status.FAILED, job="a", age_minutes=10)
    run(SyncRun.Status.FAILED, job="single")
    run(SyncRun.Status.FAILED, job="old", age_minutes=60 * 48)
    run(SyncRun.Status.FAILED, job="old", age_minutes=60 * 48 + 5)
    assert failures.failing_jobs() == [("jolpica-api", "a", 2)]

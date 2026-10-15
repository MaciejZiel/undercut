"""E-mail the owner when a sync job keeps failing (FR-802).

One message at the second failure in a row, then one every ten failures, so an outage that lasts
all weekend does not fill the inbox. Recipients come from ALERT_EMAIL_TO; empty means no mail.
Sending never raises: an alert problem must not break the sync it reports on.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction

from .failures import FAILING_AFTER, consecutive_failures
from .models import SyncRun

log = logging.getLogger(__name__)

REPEAT_EVERY = 10
_MAX_ERROR = 400


def should_alert(failures: int) -> bool:
    return failures == FAILING_AFTER or (failures > FAILING_AFTER and failures % REPEAT_EVERY == 0)


def _body(run: SyncRun, failures: int) -> str:
    last = (run.errors or [{}])[-1]
    error = str(last.get("error", last))[:_MAX_ERROR]
    return (
        f"The sync job {run.source}/{run.job} has failed {failures} times in a row.\n\n"
        f"Last error: {error}\n\n"
        f"Started: {run.started_at:%Y-%m-%d %H:%M} UTC\n"
        f"Scope: {run.scope}\n\n"
        "What to do: look at the worker log (~/services/logs/undercut-worker.log) and at\n"
        "`manage.py check_pipeline`. When the cause is fixed, run the job again, for a race:\n"
        "`manage.py resync_round <year> <round>`.\n"
        f"{settings.SITE_URL}\n"
    )


def notify(run: SyncRun) -> bool:
    """Send the alert for a failed run when it is due. Returns whether a mail went out."""
    recipients = list(settings.ALERT_EMAIL_TO)
    if not recipients or run.status != SyncRun.Status.FAILED or run.scope.get("alerted"):
        return False
    failures = consecutive_failures(run.source, run.job)
    if not should_alert(failures):
        return False
    try:
        EmailMessage(
            subject=f"[Undercut] Sync failing: {run.source}/{run.job} ({failures} in a row)",
            body=_body(run, failures),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        ).send()
    except Exception:
        log.exception("Could not send the sync failure alert for run %s", run.pk)
        return False
    SyncRun.objects.filter(pk=run.pk).update(scope={**run.scope, "alerted": True})
    log.warning("Sync failure alert sent for %s/%s (%s in a row)", run.source, run.job, failures)
    return True


def on_sync_run_saved(sender, instance: SyncRun, **kwargs) -> None:
    if instance.status == SyncRun.Status.FAILED:
        transaction.on_commit(lambda: notify(instance))

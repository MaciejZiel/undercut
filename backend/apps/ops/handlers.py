"""Weekly health mail: proof that outgoing e-mail still works, plus the pipeline state.

Brevo (and most SMTP providers) disable a key that has not been used for 90 days. A quiet
off-season can easily last that long, so the scheduler sends this mail every Monday. A failure to
send is raised so the outbox retries it and, in the end, `check_pipeline` reports a dead event.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage

from apps.events.registry import subscribe

from .status import outbox_stats, pipeline_problems

log = logging.getLogger(__name__)

EVENT = "WeeklyHealthMailDue"


def build_report() -> tuple[str, str]:
    problems = pipeline_problems()
    outbox = outbox_stats()
    status = "all good" if not problems else f"{len(problems)} problem(s)"
    lines = [
        f"Undercut weekly check: {status}.",
        "",
        f"Outbox: {outbox['pending']} pending, {outbox['dead']} dead.",
    ]
    lines += [f"PROBLEM {p.code}: {p.message}" for p in problems]
    lines += ["", "This mail also keeps the SMTP key in use.", settings.SITE_URL]
    prefix = "[Undercut] " + ("Weekly check" if not problems else "Weekly check: needs attention")
    return prefix, "\n".join(lines) + "\n"


def on_weekly_health_due(event) -> None:
    recipients = list(settings.ALERT_EMAIL_TO)
    if not recipients:
        return
    subject, body = build_report()
    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, recipients).send()
    log.info("Weekly health mail sent")


def register() -> None:
    subscribe(EVENT)(on_weekly_health_due)

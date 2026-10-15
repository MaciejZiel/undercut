"""Post-race e-mail (FR-505).

Exactly-once per (user, round) comes from the ``SentEmail`` marker, created in the same
transaction right before the message is handed to the mail backend; if sending raises, the
transaction (a savepoint) rolls the marker back. Delivery of the event is at-least-once, so a
re-delivery finds the markers and sends only what is still missing.

Why failures do not simply raise: the outbox runs a handler inside a savepoint, so raising at the
end would roll back the markers of the recipients who already got their mail, and the retry would
mail them again. Instead the handler commits the markers, and for the recipients that failed it
publishes a retry event with a backoff (first retry after 5 minutes, then 10, 20, 40 and 80:
about 2.5 hours in total, well inside the 6 hours of FR-505).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.mail import mailers
from django.db import transaction
from django.utils import timezone

from apps.accounts import selectors_public as accounts
from apps.catalog import summaries
from apps.events.publisher import publish
from apps.events.registry import subscribe
from apps.predictions import selectors_public as predictions

from . import emails
from .models import NotificationPref, SentEmail

logger = logging.getLogger(__name__)

PREDICTIONS_SCORED = "PredictionsScored"
RETRY_EVENT = "RaceResultEmailRetry"
MAX_RETRIES = 5
RETRY_BASE = timedelta(minutes=5)


@dataclass
class SendReport:
    sent: int = 0
    skipped: int = 0
    failed: list[int] = field(default_factory=list)


def send_round_emails(round_id: int) -> SendReport:
    """Send the race e-mail of a round to everyone eligible who has not got it yet."""
    report = SendReport()
    summary = summaries.race_summary(round_id)
    if summary is None or not summary.has_result:
        return report
    ref = f"round:{round_id}"
    with mailers.default as connection:  # one connection for the whole batch
        for recipient in accounts.iter_race_email_recipients():
            try:
                with transaction.atomic():
                    outcome = _send_one(connection, summary, ref, recipient.user_id)
            except Exception:
                logger.exception("Race e-mail to user %s for %s failed", recipient.user_id, ref)
                report.failed.append(recipient.user_id)
                continue
            if outcome:
                report.sent += 1
            else:
                report.skipped += 1
    return report


def _send_one(connection, summary, ref: str, user_id: int) -> bool:
    """True when an e-mail was sent. Runs inside the caller's transaction."""
    # Re-checked now: the user may have unsubscribed since the event was published.
    recipient = accounts.get_race_email_recipient(user_id)
    if recipient is None:
        return False
    token = (
        NotificationPref.objects.filter(user_id=user_id, race_result_email=True)
        .values_list("unsubscribe_token", flat=True)
        .first()
    )
    if token is None:
        return False
    _, created = SentEmail.objects.get_or_create(
        user_id=user_id, kind=emails.KIND_RACE_RESULT, ref=ref
    )
    if not created:
        return False
    round_id = summary.header.round_id
    driver_ids, constructor_ids = accounts.favorite_ids(user_id)
    content = emails.RaceEmail(
        summary=summary,
        recipient_name=recipient.display_name,
        drivers=list(summaries.driver_results(round_id, driver_ids).values()),
        constructors=list(summaries.constructor_results(round_id, constructor_ids).values()),
        pick=predictions.user_round_result(user_id, round_id),
        unsubscribe_url=emails.unsubscribe_url(token),
    )
    connection.send_messages([emails.build_message(content, recipient.email)])
    return True


def handle_race_result(event) -> None:
    """``PredictionsScored`` (or its retry): mail the round's result.

    ``SessionResultsFinalized`` is also delivered here but ignored: the mail needs the scored
    predictions, so it waits for ``PredictionsScored``.
    """
    if event.type not in (PREDICTIONS_SCORED, RETRY_EVENT):
        return
    round_id = event.payload["round_id"]
    attempt = int(event.payload.get("attempt", 0))
    report = send_round_emails(round_id)
    logger.info(
        "Race e-mails for round %s: sent %s, skipped %s, failed %s",
        round_id,
        report.sent,
        report.skipped,
        len(report.failed),
    )
    if not report.failed:
        return
    if attempt >= MAX_RETRIES:
        logger.error(
            "Giving up on %s race e-mails for round %s after %s retries",
            len(report.failed),
            round_id,
            attempt,
        )
        return
    delay = RETRY_BASE * 2**attempt
    publish(
        RETRY_EVENT,
        key=f"round:{round_id}",
        payload={"round_id": round_id, "attempt": attempt + 1},
        available_at=timezone.now() + delay,
    )


def register_handlers() -> None:
    for event_type in ("SessionResultsFinalized", PREDICTIONS_SCORED, RETRY_EVENT):
        subscribe(event_type)(handle_race_result)

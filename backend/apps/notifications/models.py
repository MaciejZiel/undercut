import secrets

from django.conf import settings
from django.db import models


def new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


class NotificationPref(models.Model):
    """E-mail preferences of one user. Created lazily on first access."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_pref"
    )
    # Opt-in (FR-505): off by default.
    race_result_email = models.BooleanField(default=False)
    # Goes into e-mail footers; lets the recipient opt out with one click and no login.
    unsubscribe_token = models.CharField(
        max_length=64, unique=True, default=new_unsubscribe_token, editable=False
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"prefs of user {self.user_id}"


class SentEmail(models.Model):
    """Marker that one e-mail went out: (user, kind, ref) is unique, which makes sending
    exactly-once under at-least-once event delivery. Deleted together with the account."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_emails"
    )
    kind = models.CharField(max_length=40)
    # What the e-mail was about, e.g. "round:12".
    ref = models.CharField(max_length=100)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "kind", "ref"], name="notifications_sent_uniq")
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.ref} -> user {self.user_id}"

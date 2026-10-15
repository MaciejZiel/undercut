"""Small public read functions of accounts for other modules (no model imports needed)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from django.contrib.auth import get_user_model

from .models import Favorite

CHUNK = 500


@dataclass(frozen=True)
class MailRecipient:
    user_id: int
    email: str
    display_name: str


def _mailable():
    """Users who may receive race-result e-mails right now.

    Opted in, active, verified address, a real person (never the demo account or its bots).
    """
    return (
        get_user_model()
        .objects.filter(
            notification_pref__race_result_email=True,
            is_active=True,
            email_verified=True,
            is_demo=False,
        )
        .exclude(email="")
    )


def _recipient(row: tuple) -> MailRecipient:
    user_id, email, display_name, username = row
    return MailRecipient(user_id, email, display_name or username)


_FIELDS = ("pk", "email", "display_name", "username")


def iter_race_email_recipients() -> Iterator[MailRecipient]:
    """Eligible recipients in id order, read in chunks (never the whole table at once)."""
    last = 0
    while True:
        rows = list(_mailable().filter(pk__gt=last).order_by("pk").values_list(*_FIELDS)[:CHUNK])
        if not rows:
            return
        for row in rows:
            yield _recipient(row)
        last = rows[-1][0]


def get_race_email_recipient(user_id: int) -> MailRecipient | None:
    """The same eligibility check for one user (used again right before sending)."""
    row = _mailable().filter(pk=user_id).values_list(*_FIELDS).first()
    return _recipient(row) if row else None


def favorite_ids(user_id: int) -> tuple[list[int], list[int]]:
    """(driver ids, constructor ids) the user follows, oldest favourite first."""
    rows = Favorite.objects.filter(user_id=user_id).values_list("driver_id", "constructor_id")
    drivers = [d for d, _ in rows if d is not None]
    constructors = [c for _, c in rows if c is not None]
    return drivers, constructors


def is_demo_user_id(user_id: int | None) -> bool:
    return bool(user_id) and get_user_model().objects.filter(pk=user_id, is_demo=True).exists()


def demo_user_ids() -> set[int]:
    """Ids of the demo account and its bots, for modules that rank or count real players only."""
    return set(get_user_model().objects.filter(is_demo=True).values_list("pk", flat=True))


def without_demo(user_ids: Iterable[int]) -> list[int]:
    demo = demo_user_ids()
    return [u for u in user_ids if u not in demo]

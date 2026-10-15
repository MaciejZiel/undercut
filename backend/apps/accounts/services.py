"""Account use cases. Views stay thin; everything that must be atomic lives here."""

import logging
from dataclasses import dataclass
from typing import Literal

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.events.publisher import publish
from apps.notifications import services as notifications

from . import exports
from .models import Favorite
from .validators import validate_display_name, validate_timezone

logger = logging.getLogger(__name__)
User = get_user_model()

register_export_provider = exports.register_export_provider

MAX_FAVORITE_DRIVERS = 10
MAX_FAVORITE_CONSTRUCTORS = 5
THEMES = ("system", "light", "dark")

DEMO_USERNAME = "demo"
DEMO_DISPLAY_NAME = "Demo"
# Starting favourites of the demo account (slugs; entries missing from the catalog are skipped).
DEMO_FAVORITE_DRIVERS = ("max-verstappen", "norris", "leclerc")
DEMO_FAVORITE_CONSTRUCTORS = ("red-bull", "mclaren")

FavoriteKind = Literal["driver", "constructor"]


class AccountError(Exception):
    """A business rule was broken; ``code`` is stable and machine readable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class DemoLocked(AccountError, PermissionDenied):
    def __init__(self):
        super().__init__("demo_locked", "The demo account cannot do this.")


class NotFound(AccountError):
    pass


class LimitReached(AccountError):
    pass


# --- Settings ---------------------------------------------------------------------------------


@dataclass
class SettingsUpdate:
    display_name: str | None = None
    timezone: str | None = None
    theme: str | None = None
    race_result_email: bool | None = None


def email_verified_for(user) -> bool:
    """Whether the user's primary e-mail address is confirmed."""
    return EmailAddress.objects.filter(user=user, primary=True, verified=True).exists()


def sync_email_verified(user) -> None:
    """Mirror allauth's e-mail state into ``User.email_verified`` (cheap flag for other modules)."""
    verified = email_verified_for(user)
    if user.email_verified != verified:
        User.objects.filter(pk=user.pk).update(email_verified=verified)
        user.email_verified = verified


def update_settings(user, update: SettingsUpdate) -> None:
    """Apply a partial settings update. Raises ValidationError / DemoLocked."""
    fields: list[str] = []
    if update.display_name is not None:
        if user.is_demo:
            raise DemoLocked()
        name = validate_display_name(update.display_name)
        if name != user.display_name:
            if User.objects.filter(display_name__iexact=name).exclude(pk=user.pk).exists():
                raise ValidationError("This display name is already taken.", code="taken")
            user.display_name = name
            fields.append("display_name")
    if update.timezone is not None:
        user.timezone = validate_timezone(update.timezone)
        fields.append("timezone")
    if update.theme is not None:
        if update.theme not in THEMES:
            raise ValidationError("Unknown theme.", code="invalid_theme")
        user.theme = update.theme
        fields.append("theme")
    with transaction.atomic():
        if fields:
            try:
                user.save(update_fields=fields)
            except IntegrityError:
                raise ValidationError("This display name is already taken.", code="taken") from None
        if update.race_result_email is not None:
            notifications.set_race_result_email(user, update.race_result_email)


# --- Favorites --------------------------------------------------------------------------------

_KIND_LIMITS = {"driver": MAX_FAVORITE_DRIVERS, "constructor": MAX_FAVORITE_CONSTRUCTORS}


def _target_model(kind: FavoriteKind):
    # Resolved through the FK so this module never imports catalog's models.
    return Favorite._meta.get_field(kind).related_model


def _resolve(kind: FavoriteKind, slug: str):
    target = _target_model(kind)._default_manager.filter(slug=slug).first()
    if target is None:
        raise NotFound("not_found", f"Unknown {kind}.")
    return target


def add_favorite(user, kind: FavoriteKind, slug: str) -> bool:
    """Idempotent. Returns True when a favourite was created, False if it already existed."""
    target = _resolve(kind, slug)
    with transaction.atomic():
        # Serialise concurrent adds of one user so the limit cannot be overshot.
        User.objects.select_for_update().get(pk=user.pk)
        mine = Favorite.objects.filter(user=user, **{f"{kind}__isnull": False})
        if mine.filter(**{kind: target}).exists():
            return False
        if mine.count() >= _KIND_LIMITS[kind]:
            raise LimitReached(
                "favorites_limit",
                f"You can follow at most {_KIND_LIMITS[kind]} {kind}s.",
            )
        Favorite.objects.create(user=user, **{kind: target})
    return True


def remove_favorite(user, kind: FavoriteKind, slug: str) -> bool:
    """Idempotent. Returns True when something was removed."""
    deleted, _ = Favorite.objects.filter(user=user, **{f"{kind}__slug": slug}).delete()
    return deleted > 0


def list_favorites(user) -> dict[str, list]:
    rows = Favorite.objects.filter(user=user).select_related("driver", "constructor")
    return {
        "drivers": [f.driver for f in rows if f.driver_id],
        "constructors": [f.constructor for f in rows if f.constructor_id],
    }


def reset_favorites(user, *, drivers=(), constructors=()) -> None:
    """Replace all favourites with the given slugs (unknown slugs are skipped)."""
    with transaction.atomic():
        Favorite.objects.filter(user=user).delete()
        for kind, slugs in (("driver", drivers), ("constructor", constructors)):
            for slug in slugs:
                try:
                    add_favorite(user, kind, slug)
                except NotFound:
                    logger.warning("Demo favourite %s %r is not in the catalog", kind, slug)


# --- Export -----------------------------------------------------------------------------------


def profile_data(user) -> dict:
    return {
        "id": user.pk,
        "display_name": user.display_name,
        "email": user.email,
        "email_verified": user.email_verified,
        "timezone": user.timezone,
        "theme": user.theme,
        "date_joined": user.date_joined.isoformat(),
    }


def export_user_data(user) -> dict:
    """Profile, favourites and whatever other modules contribute through export providers."""
    favorites = list_favorites(user)
    data = {
        "exported_at": timezone.now().isoformat(),
        "profile": profile_data(user),
        "favorites": {
            "drivers": [d.slug for d in favorites["drivers"]],
            "constructors": [c.slug for c in favorites["constructors"]],
        },
    }
    data.update(exports.collect(user))
    return data


# --- Deletion ---------------------------------------------------------------------------------


def delete_account(user, confirmation: str) -> None:
    """Delete the account immediately and irreversibly.

    The ``UserDeleted`` event goes to the outbox in the same transaction, so other modules clean up
    what they own (or anonymise it) exactly when the account disappears.
    """
    if user.is_demo:
        raise DemoLocked()
    if not user.display_name or confirmation.strip() != user.display_name:
        raise AccountError("confirmation_mismatch", "Type your display name to confirm.")
    user_id = user.pk
    with transaction.atomic():
        publish("UserDeleted", key=f"user:{user_id}", payload={"user_id": user_id})
        _drop_sessions(user_id)
        User.objects.filter(pk=user_id).delete()


def _drop_sessions(user_id: int) -> None:
    """Invalidate every session of the user (the table is small: scan the live ones)."""
    doomed = [
        s.pk
        for s in Session.objects.filter(expire_date__gt=timezone.now())
        if str(s.get_decoded().get("_auth_user_id")) == str(user_id)
    ]
    Session.objects.filter(pk__in=doomed).delete()


# --- Demo account -----------------------------------------------------------------------------


def get_demo_user():
    return User.objects.filter(username=DEMO_USERNAME, is_demo=True).first()


def ensure_demo_user():
    """Create the shared, locked demo account (or repair it). Returns the user."""
    user = get_demo_user()
    if user is None:
        user = User(username=DEMO_USERNAME, is_demo=True)
    user.display_name = DEMO_DISPLAY_NAME
    user.email = ""  # no e-mail: it cannot be reached through login or password reset
    user.email_verified = True
    user.is_active = True
    user.is_staff = user.is_superuser = False
    user.set_unusable_password()
    user.save()
    EmailAddress.objects.filter(user=user).delete()
    return user


def reset_demo_account() -> None:
    """Return the demo account to its initial state. Idempotent."""
    user = get_demo_user()
    if user is None:
        logger.info("No demo account; nothing to reset")
        return
    reset_favorites(user, drivers=DEMO_FAVORITE_DRIVERS, constructors=DEMO_FAVORITE_CONSTRUCTORS)
    # TODO: reset the demo account's predictions (predictions module, via its own handler/export).

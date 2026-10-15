"""Google sign-in use cases: log in, sign up, link and unlink. Views stay thin."""

import logging
import re
import secrets

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model, login
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .google import GoogleError
from .models import GoogleIdentity
from .validators import DISPLAY_NAME_MAX, validate_display_name

logger = logging.getLogger(__name__)
User = get_user_model()

BACKEND = "django.contrib.auth.backends.ModelBackend"
_NAME_CHARS = re.compile(r"[^\w.\- ]+")


def _base_display_name(name: str, email: str) -> str:
    """A valid display name from the Google profile; falls back to the e-mail's local part."""
    for source in (name, email.split("@")[0]):
        candidate = " ".join(_NAME_CHARS.sub("", source).split())[:DISPLAY_NAME_MAX].strip(" .-")
        try:
            return validate_display_name(candidate)
        except ValidationError:
            continue
    return "Fan"


def _free_display_name(name: str, email: str) -> str:
    base = _base_display_name(name, email)
    candidate = base
    while User.objects.filter(display_name__iexact=candidate).exists():
        suffix = str(secrets.randbelow(9000) + 1000)
        candidate = f"{base[: DISPLAY_NAME_MAX - len(suffix) - 1]} {suffix}"
    return candidate


def _login(request, user) -> None:
    login(request, user, backend=BACKEND)


def _check_usable(user) -> None:
    if not user.is_active or user.is_demo:
        raise GoogleError("account_unavailable", "This account cannot sign in.")


def _create_user(claims: dict):
    """New account from a verified Google identity. Retries when a display name race is lost."""
    for _ in range(5):
        try:
            with transaction.atomic():
                user = User(
                    username=f"g_{secrets.token_hex(12)}",
                    email=claims["email"],
                    display_name=_free_display_name(claims["name"], claims["email"]),
                    email_verified=True,
                )
                user.set_unusable_password()
                user.save()
                EmailAddress.objects.create(
                    user=user, email=claims["email"], primary=True, verified=True
                )
                GoogleIdentity.objects.create(user=user, sub=claims["sub"], email=claims["email"])
                return user
        except IntegrityError:
            existing = GoogleIdentity.objects.filter(sub=claims["sub"]).select_related("user")
            found = existing.first()
            if found is not None:  # the same person finished a parallel sign-in first
                return found.user
    raise GoogleError("unavailable", "Could not create the account.")


def sign_in(request, claims: dict):
    """Log in (or sign up) with verified Google claims and return the user."""
    identity = GoogleIdentity.objects.select_related("user").filter(sub=claims["sub"]).first()
    if identity is not None:
        user = identity.user
        _check_usable(user)
        _login(request, user)
        return user

    match = EmailAddress.objects.select_related("user").filter(email__iexact=claims["email"])
    owner = match.first()
    if owner is None:
        # An address that exists only on User.email (not in allauth) is treated the same way.
        stray = User.objects.filter(email__iexact=claims["email"]).first()
        if stray is not None:
            raise GoogleError("email_taken", "An account with this e-mail already exists.")
        user = _create_user(claims)
        _check_usable(user)
        _login(request, user)
        logger.info("Google sign-up: user %s", user.pk)
        return user

    # Linking by e-mail is only safe when the existing address is verified: otherwise whoever made
    # the account first (and knows its password) would gain access to the real owner's Google login.
    if not owner.verified:
        raise GoogleError(
            "email_unverified_account",
            "An unverified account uses this e-mail. Confirm it or reset the password first.",
        )
    user = owner.user
    _check_usable(user)
    try:
        with transaction.atomic():
            GoogleIdentity.objects.create(user=user, sub=claims["sub"], email=claims["email"])
    except IntegrityError:
        raise GoogleError("already_linked", "This account already has a Google login.") from None
    _login(request, user)
    logger.info("Google linked to existing user %s", user.pk)
    return user


def link(user, claims: dict) -> None:
    """Attach a Google account to the signed-in ``user``."""
    _check_usable(user)
    try:
        with transaction.atomic():
            GoogleIdentity.objects.create(user=user, sub=claims["sub"], email=claims["email"])
    except IntegrityError:
        taken = GoogleIdentity.objects.filter(sub=claims["sub"]).exclude(user=user).exists()
        raise GoogleError(
            "google_in_use" if taken else "already_linked",
            "That Google account is already linked." if taken else "Google is already linked.",
        ) from None


def unlink(user) -> None:
    """Remove the Google login. Refused when it is the account's only way to sign in."""
    if not user.has_usable_password():
        raise GoogleError("last_login_method", "Set a password first.")
    GoogleIdentity.objects.filter(user=user).delete()


def status_for(user) -> dict:
    identity = GoogleIdentity.objects.filter(user=user).first() if user.is_authenticated else None
    return {
        "linked": identity is not None,
        "email": identity.email if identity else None,
        "has_password": bool(user.is_authenticated and user.has_usable_password()),
    }

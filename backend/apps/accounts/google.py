"""Minimal Google sign-in (OpenID Connect authorization code flow with PKCE), standard library only.

The ID token is read without checking its signature. That is allowed by OpenID Connect Core 3.1.3.7
because it arrives straight from Google's token endpoint over TLS (system trust store), never from
the browser. Everything else is still checked: issuer, audience, expiry, nonce, verified e-mail.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 64 * 1024
CLOCK_SKEW_SECONDS = 60
FLOW_TTL_SECONDS = 600


class GoogleError(Exception):
    """A failed sign-in. ``code`` is a stable machine-readable reason shown to the user."""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


def enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def new_flow() -> dict:
    """Fresh one-time values for a sign-in attempt. Kept in the session, never in the URL."""
    return {
        "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32),
        "verifier": secrets.token_urlsafe(64),
        "started": int(time.time()),
    }


def authorization_url(flow: dict) -> str:
    challenge = _b64url(hashlib.sha256(flow["verifier"].encode("ascii")).digest())
    query = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": flow["state"],
        "nonce": flow["nonce"],
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(query)}"


def check_state(flow: dict | None, returned_state: str) -> dict:
    """Return the flow when ``returned_state`` matches and is fresh, else raise GoogleError."""
    if not flow or not returned_state:
        raise GoogleError("invalid_state", "No sign-in in progress.")
    if not hmac.compare_digest(str(flow.get("state", "")), returned_state):
        raise GoogleError("invalid_state", "State mismatch.")
    if time.time() - int(flow.get("started", 0)) > FLOW_TTL_SECONDS:
        raise GoogleError("expired", "The sign-in took too long.")
    return flow


def _post_token(code: str, verifier: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    ).encode("ascii")
    request = urllib.request.Request(  # noqa: S310 (fixed https URL)
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        # 400 invalid_grant: code used twice or expired. Never log the body (it may echo codes).
        logger.warning("Google token endpoint answered %s", exc.code)
        raise GoogleError("exchange_failed", f"HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Google token endpoint unreachable: %s", type(exc).__name__)
        raise GoogleError("unavailable", "Google could not be reached.") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise GoogleError("exchange_failed", "Response too large.")
    try:
        data = json.loads(raw)
    except ValueError:
        raise GoogleError("exchange_failed", "Malformed response.") from None
    if not isinstance(data, dict):
        raise GoogleError("exchange_failed", "Malformed response.")
    return data


def _payload(id_token: object) -> dict:
    if not isinstance(id_token, str) or id_token.count(".") != 2:
        raise GoogleError("invalid_token", "Missing ID token.")
    segment = id_token.split(".")[1]
    try:
        claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
    except (ValueError, UnicodeDecodeError):
        raise GoogleError("invalid_token", "Unreadable ID token.") from None
    if not isinstance(claims, dict):
        raise GoogleError("invalid_token", "Unreadable ID token.")
    return claims


def validate_claims(claims: dict, nonce: str, *, now: float | None = None) -> dict:
    """Check the ID token claims and return the ones we use: sub, email, name."""
    now = time.time() if now is None else now
    if claims.get("iss") not in ISSUERS:
        raise GoogleError("invalid_token", "Wrong issuer.")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if settings.GOOGLE_CLIENT_ID not in audiences:
        raise GoogleError("invalid_token", "Wrong audience.")
    exp = claims.get("exp")
    if not isinstance(exp, int | float) or exp + CLOCK_SKEW_SECONDS < now:
        raise GoogleError("invalid_token", "Token expired.")
    if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise GoogleError("invalid_token", "Nonce mismatch.")
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise GoogleError("invalid_token", "Missing subject.")
    email = claims.get("email")
    if not isinstance(email, str) or "@" not in email:
        raise GoogleError("email_missing", "No e-mail address.")
    # Google sends a boolean; tolerate the string form some libraries produce, nothing else.
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleError("email_unverified", "Google has not verified this e-mail address.")
    name = claims.get("name")
    return {
        "sub": sub,
        "email": email.strip().lower(),
        "name": name if isinstance(name, str) else "",
    }


def exchange_code(code: str, flow: dict) -> dict:
    """Trade the authorization code for the user's verified identity (sub, email, name)."""
    if not code:
        raise GoogleError("exchange_failed", "No code.")
    tokens = _post_token(code, flow["verifier"])
    return validate_claims(_payload(tokens.get("id_token")), flow["nonce"])

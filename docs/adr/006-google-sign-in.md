# ADR 006: Google sign-in without a new dependency

Status: accepted

## Context
FR-502 asks for Google login. allauth's `socialaccount` extra would pull in `requests` and with it
`certifi` (MPL-2.0, copyleft), which needs written approval from Company Management. Everything
else in the stack is permissively licensed.

## Decision
A small OpenID Connect authorization-code client in `apps/accounts/google.py`, using only the
standard library (`urllib`, system trust store). The flow uses `state`, `nonce` and PKCE (S256), all
kept in the session and consumed on first use, with a 10 minute lifetime.

The ID token is read without checking its signature: it comes straight from Google's token endpoint
over TLS, which OpenID Connect Core 3.1.3.7 allows. Issuer, audience, expiry, nonce, subject and a
verified e-mail are still enforced.

Account rules (`apps/accounts/google_login.py`):
- A known Google `sub` signs in, even if the e-mail changed later.
- An unknown `sub` whose e-mail matches a **verified** local address is linked to that account.
- A match with an **unverified** local address is refused: whoever created that account first could
  otherwise ride on the real owner's Google login.
- No match creates an account with a verified e-mail and no password.
- Google can only be unlinked when the account has a password, so nobody locks themselves out.
- The return path is accepted only as a same-site path (no open redirect).

## Consequences
- No new entry in `3rdparty_licenses.md`.
- Roughly 300 lines of security-relevant code to maintain, covered by `tests/accounts/test_google.py`.
- Setup: create an OAuth client (web application) in the Google console with the redirect URI
  `https://<host>/api/v1/auth/google/callback/`, then set `GOOGLE_CLIENT_ID` and
  `GOOGLE_CLIENT_SECRET`. Without both, the button is hidden and the endpoints refuse.

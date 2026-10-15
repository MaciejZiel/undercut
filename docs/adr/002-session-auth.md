# ADR 002: Session authentication with allauth headless

Status: accepted

## Context
Frontend and API share one origin behind the reverse proxy. Account flows (registration,
e-mail verification, password reset, optional Google login) are security-sensitive.

## Decision
Django sessions with CSRF protection, and `django-allauth` in headless mode for the flows.
Nothing is hand-rolled: tokens, verification and reset links come from allauth. Login attempts
are rate-limited per IP and per account. The admin is restricted at the network level.

## Consequences
- No JWT handling in the browser; a session can be revoked server-side on password change
  or account deletion.
- Cookies are `SameSite=Lax`; the frontend sends the CSRF header on mutations.

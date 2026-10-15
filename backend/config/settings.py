"""Django settings for Undercut.

All environment-specific values come from environment variables (see .env.example).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.headless",
    # Undercut modules. Import rules between them are enforced by import-linter.
    "apps.accounts",
    "apps.events",
    "apps.catalog",
    "apps.ingestion",
    "apps.standings",
    "apps.analytics",
    "apps.predictions",
    "apps.notifications",
    "apps.webcache",
]

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.accounts.middleware.DemoRestrictionsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL only: the project relies on unaccent, pg_trgm, JSONB and SKIP LOCKED.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://undercut:undercut@localhost:5432/undercut",
    )
}

_cache_url = env("CACHE_URL", default="")
if _cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _cache_url,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "undercut",
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session auth + CSRF: frontend and API share one origin behind the reverse proxy.
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["apps.core.throttling.PublicAnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
    # Behind nginx the peer is always 127.0.0.1; nginx puts the real client IP in
    # X-Forwarded-For, so set DRF_NUM_PROXIES=1 there to throttle per visitor.
    "NUM_PROXIES": env.int("DRF_NUM_PROXIES", default=None),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Undercut API",
    "DESCRIPTION": "Formula 1 stats, analytics and predictions.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"


# --- Accounts (django-allauth in headless mode, session based) ---------------------------------
# Google login (FR-502) is not configured: it needs allauth's "socialaccount" extra, which pulls
# in requests -> certifi (MPL-2.0, copyleft). That requires written approval first.
ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_SIGNUP_FORM_CLASS = "apps.accounts.forms.SignupExtraFieldsForm"
# "optional": an unverified account may log in and browse, but cannot act (see can_predict).
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True


def ACCOUNT_USER_DISPLAY(user):  # noqa: N802 (allauth setting name)
    """Name used in e-mails: the public display name, never the generated username."""
    return user.display_name or "there"


ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Undercut] "
# Login attempts: 5 failures per 15 minutes per IP and per account (cache based; the local-memory
# cache is enough on a single-host deployment).
ACCOUNT_RATE_LIMITS = {"login_failed": "5/15m/ip,5/15m/key"}
# Password reset links are valid for one hour (the allauth token generator uses this setting).
PASSWORD_RESET_TIMEOUT = 60 * 60

HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": "/account/verify-email/{key}",
    "account_reset_password": "/account/password/reset",
    "account_reset_password_from_key": "/account/password/reset/key/{key}",
    "account_signup": "/account/signup",
}
# Same knob as DRF_NUM_PROXIES: number of trusted reverse proxies in front of Django. Needed so the
# login rate limit sees the visitor's IP and not the proxy's.
ALLAUTH_TRUSTED_PROXY_COUNT = env.int("DRF_NUM_PROXIES", default=0) or 0

# --- E-mail ------------------------------------------------------------------------------------
# Django 6.1 MAILERS (the EMAIL_* settings are deprecated). Console in DEBUG, SMTP otherwise; the
# SMTP server comes from env vars. Tests swap in the in-memory backend automatically.
# Without EMAIL_HOST (no SMTP provider configured yet) mail is written to stdout instead of failing
# every sign-up with a connection error; the supervisors keep that in the service log.
# (not named EMAIL_HOST: Django 6.1 rejects the deprecated setting names next to MAILERS)
_smtp_host = env("EMAIL_HOST", default="")
if DEBUG or not _smtp_host:
    MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
else:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": _smtp_host,
                "port": env.int("EMAIL_PORT", default=587),
                "username": env("EMAIL_HOST_USER", default=""),
                "password": env("EMAIL_HOST_PASSWORD", default=""),
                "use_tls": env.bool("EMAIL_USE_TLS", default=True),
                "use_ssl": env.bool("EMAIL_USE_SSL", default=False),
                "timeout": env.int("EMAIL_TIMEOUT", default=10),
            },
        }
    }
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Undercut <noreply@localhost>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Frontend page cache: purged by apps.webcache after data changes. Same secret as the
# frontend's REVALIDATE_SECRET; empty disables purging (local development without the frontend).
REVALIDATE_URL = env("REVALIDATE_URL", default="http://127.0.0.1:3000/_internal/revalidate")
REVALIDATE_SECRET = env("REVALIDATE_SECRET", default="")

# --- Post-race e-mail (FR-505) -----------------------------------------------------------------
# Public address of the site, used for links in e-mails (no trailing slash).
SITE_URL = env("SITE_URL", default="https://undercut.maciejzielinski.dev").rstrip("/")
# Public base of the API, for the one-click unsubscribe link (defaults to the site itself).
API_PUBLIC_URL = env("API_PUBLIC_URL", default=SITE_URL).rstrip("/")


# === Production operations (apps.ops): logging, Sentry, security review =========================
INSTALLED_APPS += ["apps.ops"]
# First in the chain, so the request id exists for every later middleware and log line.
MIDDLEWARE = ["apps.ops.middleware.RequestIdMiddleware", *MIDDLEWARE]

# Logging: JSON lines on stdout when DEBUG is off (the supervisors append stdout to
# ~/services/logs/undercut-*.log), plain text in development. LOG_FORMAT=json|text overrides.
LOG_FORMAT = env("LOG_FORMAT", default="text" if DEBUG else "json")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.ops.logging.RequestIdFilter"},
        "redact": {"()": "apps.ops.logging.RedactionFilter"},
    },
    "formatters": {
        "json": {"()": "apps.ops.logging.JsonFormatter"},
        "text": {"format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json" if LOG_FORMAT == "json" else "text",
            # Order matters: request_id first, then redaction of the final message.
            "filters": ["request_id", "redact"],
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        # Our middleware writes the access line; Django's own 4xx/5xx request log would double it.
        "django.request": {"level": "ERROR"},
    },
}

# Sentry: off unless SENTRY_DSN is set. The package is not a dependency (it pulls in certifi,
# MPL-2.0, which needs written approval); install it by hand on the server if wanted. Without it
# the app only logs a warning. No personal data, no tracing unless a rate is set.
from apps.ops.sentry import init_sentry  # noqa: E402

init_sentry(
    env("SENTRY_DSN", default=""),
    environment=env("SENTRY_ENVIRONMENT", default="production" if not DEBUG else "development"),
    traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
)

# Security review (run `manage.py check --deploy` after changing any of this).
# - SECURE_PROXY_SSL_HEADER, secure cookies, HSTS, nosniff and referrer policy are set above when
#   DEBUG is off. The header is trustworthy because gunicorn listens on loopback only and nginx
#   always sets X-Forwarded-Proto.
# - SECURE_SSL_REDIRECT stays off on purpose: TLS ends at Cloudflare, nginx speaks plain HTTP on
#   loopback, and a redirect would break the local health checks. HTTPS is enforced at the edge.
# - HSTS does not include subdomains: maciejzielinski.dev hosts other, unrelated apps.
# - ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS come from DJANGO_ALLOWED_HOSTS and
#   DJANGO_CSRF_TRUSTED_ORIGINS (empty by default, so nothing is accepted by accident).
# - The session cookie is HttpOnly. The CSRF cookie must stay readable by the frontend, so it is
#   not HttpOnly (Django's default).
# - /admin/ is reachable only from localhost or Tailscale (nginx-server.conf); keep it that way.
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
# Same ceiling as nginx's client_max_body_size.
DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024
# Deliberate: see the notes above (no subdomain HSTS, no preload, TLS redirect done at the edge).
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W008", "security.W021"]

# Shared secret that lets the Next.js server's own API calls skip the anonymous rate limit
# (see apps.core.throttling). Same value as the frontend's INTERNAL_API_TOKEN; empty = no exemption.
INTERNAL_API_TOKEN = env("INTERNAL_API_TOKEN", default="")

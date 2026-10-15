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
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
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
if DEBUG:
    MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
else:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": env("EMAIL_HOST", default="localhost"),
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

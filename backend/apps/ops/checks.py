from django.conf import settings
from django.core.checks import Tags, Warning, register  # noqa: A004


@register(Tags.security, deploy=True)
def production_settings(app_configs, **kwargs):
    """Extra `manage.py check --deploy` rules for this project."""
    issues = []
    if str(settings.SECRET_KEY).startswith("dev-only"):
        issues.append(
            Warning(
                "DJANGO_SECRET_KEY is the built-in development key.",
                hint="Set a long random DJANGO_SECRET_KEY in the env file.",
                id="ops.W001",
            )
        )
    if not settings.ALLOWED_HOSTS:
        issues.append(
            Warning(
                "DJANGO_ALLOWED_HOSTS is empty: every request will be rejected.",
                id="ops.W002",
            )
        )
    if not settings.CSRF_TRUSTED_ORIGINS:
        issues.append(
            Warning(
                "DJANGO_CSRF_TRUSTED_ORIGINS is empty: logins and writes through the public "
                "host will fail CSRF checks.",
                id="ops.W003",
            )
        )
    return issues

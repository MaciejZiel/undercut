import re
from functools import lru_cache
from zoneinfo import available_timezones

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

DISPLAY_NAME_MIN = 3
DISPLAY_NAME_MAX = 20
# Letters, digits, underscore, dot, hyphen and single inner spaces.
DISPLAY_NAME_RE = re.compile(r"^[\w.\-]+(?: [\w.\-]+)*$")
RESERVED_DISPLAY_NAMES = frozenset(
    {"admin", "administrator", "undercut", "moderator", "staff", "support", "deleted user"}
)


def normalize_display_name(value: str) -> str:
    return " ".join(str(value).split())


def validate_display_name(value: str) -> str:
    """Return the normalised name or raise ValidationError. Uniqueness is checked elsewhere."""
    value = normalize_display_name(value)
    if not DISPLAY_NAME_MIN <= len(value) <= DISPLAY_NAME_MAX:
        raise ValidationError(
            _("Display name must be between %(min)d and %(max)d characters long."),
            params={"min": DISPLAY_NAME_MIN, "max": DISPLAY_NAME_MAX},
            code="display_name_length",
        )
    if not DISPLAY_NAME_RE.match(value):
        raise ValidationError(
            _("Display name may contain letters, digits, spaces, dots, hyphens and underscores."),
            code="display_name_chars",
        )
    if value.casefold() in RESERVED_DISPLAY_NAMES:
        raise ValidationError(_("This display name is reserved."), code="display_name_reserved")
    return value


@lru_cache(maxsize=1)
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def validate_timezone(value: str) -> str:
    if value not in _timezones():
        raise ValidationError(_("Unknown time zone."), code="invalid_timezone")
    return value

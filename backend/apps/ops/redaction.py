"""Remove secrets and personal data from text before it is logged or sent to Sentry."""

import re

REDACTED = "[redacted]"

_EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# user:password@ inside connection URLs (postgres://user:secret@host/db).
_URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*://)[^/\s:@]*:[^/\s@]*@", re.I)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
# key=value, key: value and "key": "value" for sensitive key names.
_SENSITIVE_KEYS = (
    r"password\w*|passwd|secret\w*|token\w*|api[_-]?key|authorization|cookie|set-cookie|"
    r"sessionid|csrftoken|dsn|revalidate_secret|django_secret_key"
)
_KEY_VALUE = re.compile(
    rf"""(?ix)
    (?P<key>["']?(?:{_SENSITIVE_KEYS})["']?\s*[:=]\s*)
    (?!\[redacted\])
    (?P<value>"[^"]*"|'[^']*'|[^\s,;&}}\]]+)
    """
)


def redact(text: str) -> str:
    """Mask e-mail addresses, URL credentials, bearer tokens and sensitive key=value pairs."""
    if not text:
        return text
    text = _URL_CREDENTIALS.sub(lambda m: f"{m.group('scheme')}{REDACTED}@", text)
    text = _BEARER.sub(lambda m: f"{m.group(1)} {REDACTED}", text)
    text = _KEY_VALUE.sub(lambda m: f"{m.group('key')}{REDACTED}", text)
    return _EMAIL.sub(REDACTED, text)

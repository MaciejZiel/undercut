import hmac

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle

INTERNAL_TOKEN_META = "HTTP_X_INTERNAL_TOKEN"


class PublicAnonRateThrottle(AnonRateThrottle):
    """Anonymous rate limit per client address, with one exemption.

    The Next.js server renders pages by calling this API from a single address, so without an
    exemption all visitors would share one bucket and the site would throttle itself (and the
    sitemap build would hit 429). Requests carrying the shared internal token are not limited.
    Visitors cannot use it: the token only exists in the server environments.
    """

    def allow_request(self, request, view):
        token = getattr(settings, "INTERNAL_API_TOKEN", "")
        given = request.META.get(INTERNAL_TOKEN_META, "")
        # An unset token must never match an empty header.
        if token and given and hmac.compare_digest(given.encode(), token.encode()):
            return True
        return super().allow_request(request, view)

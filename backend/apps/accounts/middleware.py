import re

from django.http import JsonResponse

# allauth endpoints that change credentials. The shared demo account must never use them.
_LOCKED_PATHS = re.compile(
    r"^/api/v1/allauth/[^/]+/v1/(account/(email|password/change|phone)|auth/reauthenticate)"
)
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class DemoRestrictionsMiddleware:
    """Server-side lock of the demo account: no e-mail or password changes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and user.is_demo
            and request.method not in _SAFE_METHODS
            and _LOCKED_PATHS.match(request.path)
        ):
            return JsonResponse(
                {"detail": "The demo account cannot do this.", "code": "demo_locked"}, status=403
            )
        return self.get_response(request)

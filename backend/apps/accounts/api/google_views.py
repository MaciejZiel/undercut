import logging

from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import google, google_login

logger = logging.getLogger(__name__)

SESSION_KEY = "google_oauth"
LOGIN_PATH = "/login"
SETTINGS_PATH = "/settings"


class GoogleStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    linked = serializers.BooleanField()
    email = serializers.EmailField(allow_null=True)
    has_password = serializers.BooleanField()


def safe_next(value: str | None) -> str:
    """A same-site path or "/". Blocks absolute URLs, //host and backslashes (open redirect)."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    if any(ord(ch) < 32 for ch in value):
        return "/"
    return value


def _redirect(path: str, **params: str) -> HttpResponseRedirect:
    from urllib.parse import urlencode

    query = f"?{urlencode(params)}" if params else ""
    response = HttpResponseRedirect(f"{path}{query}")
    response["Cache-Control"] = "no-store"
    return response


@method_decorator(never_cache, name="dispatch")
class GoogleStatusView(APIView):
    """Whether Google sign-in is available, and what is linked for the signed-in user."""

    permission_classes = [AllowAny]

    @extend_schema(responses=GoogleStatusSerializer)
    def get(self, request):
        data = google_login.status_for(request.user)
        return Response({"enabled": google.enabled(), **data})

    @extend_schema(request=None, responses={204: None})
    @method_decorator(csrf_protect)
    def delete(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Sign in first.", "code": "unauthenticated"}, status=401)
        try:
            google_login.unlink(request.user)
        except google.GoogleError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=409)
        return Response(status=204)


@method_decorator(never_cache, name="dispatch")
class GoogleStartView(APIView):
    """Begin sign-in (``?next=/path``) or, when signed in, linking (``?mode=link``)."""

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("next", str, description="Same-site path to return to."),
            OpenApiParameter("mode", str, enum=["login", "link"]),
        ],
        responses={302: None},
    )
    def get(self, request):
        mode = "link" if request.GET.get("mode") == "link" else "login"
        back = LOGIN_PATH if mode == "login" else SETTINGS_PATH
        if not google.enabled():
            return _redirect(back, google_error="disabled")
        if mode == "link" and not request.user.is_authenticated:
            return _redirect(LOGIN_PATH, google_error="unauthenticated")
        flow = google.new_flow()
        flow["mode"] = mode
        flow["next"] = safe_next(request.GET.get("next"))
        if mode == "link":
            flow["user_id"] = request.user.pk
        request.session[SESSION_KEY] = flow
        response = HttpResponseRedirect(google.authorization_url(flow))
        response["Cache-Control"] = "no-store"
        return response


@method_decorator(never_cache, name="dispatch")
class GoogleCallbackView(APIView):
    """Google sends the browser back here. The one-time flow in the session is consumed first."""

    permission_classes = [AllowAny]

    @extend_schema(responses={302: None})
    def get(self, request):
        flow = request.session.pop(SESSION_KEY, None)
        mode = (flow or {}).get("mode", "login")
        back = SETTINGS_PATH if mode == "link" else LOGIN_PATH

        def fail(code: str):
            logger.info("Google sign-in failed: %s", code)
            return _redirect(back, google_error=code)

        if not google.enabled():
            return fail("disabled")
        if request.GET.get("error"):  # the user pressed "Cancel" or Google refused
            return fail("cancelled" if request.GET["error"] == "access_denied" else "denied")
        try:
            google.check_state(flow, request.GET.get("state", ""))
            claims = google.exchange_code(request.GET.get("code", ""), flow)
            if mode == "link":
                user = request.user
                if not user.is_authenticated or user.pk != flow.get("user_id"):
                    raise google.GoogleError("unauthenticated", "The session changed.")
                google_login.link(user, claims)
                return _redirect(SETTINGS_PATH, google="linked")
            google_login.sign_in(request, claims)
        except google.GoogleError as exc:
            return fail(exc.code)
        return _redirect(flow["next"])

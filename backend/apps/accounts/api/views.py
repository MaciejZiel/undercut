import json

from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services

from . import serializers as s


def _error(code: str, message: str, http_status: int) -> Response:
    return Response({"detail": message, "code": code}, status=http_status)


def _validation_error(exc: DjangoValidationError) -> Response:
    return Response(
        {"detail": " ".join(exc.messages), "code": exc.code or "invalid"},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _me(request) -> dict:
    user = request.user
    if not user.is_authenticated:
        return {"is_authenticated": False, "user": None}
    return {"is_authenticated": True, "user": s.UserSerializer(user).data}


class CsrfView(APIView):
    """Sets the ``csrftoken`` cookie. Call once on page load, before any unsafe request."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(responses=s.CsrfSerializer)
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class MeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=s.MeSerializer)
    def get(self, request):
        return Response(_me(request))


class DemoLoginView(APIView):
    """Log in as the shared demo account ("Try without registering", FR-507)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: s.MeSerializer, 404: s.ErrorSerializer})
    @method_decorator(csrf_protect)
    def post(self, request):
        user = services.get_demo_user()
        if user is None or not user.is_active:
            return _error("demo_unavailable", "The demo account is not available.", 404)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.user = user
        return Response(_me(request))


class SettingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=s.UserSerializer)
    def get(self, request):
        return Response(s.UserSerializer(request.user).data)

    @extend_schema(
        request=s.SettingsUpdateSerializer,
        responses={200: s.UserSerializer, 400: s.ErrorSerializer, 403: s.ErrorSerializer},
    )
    def patch(self, request):
        body = s.SettingsUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            services.update_settings(request.user, services.SettingsUpdate(**body.validated_data))
        except services.DemoLocked as exc:
            return _error(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as exc:
            return _validation_error(exc)
        request.user.refresh_from_db()
        return Response(s.UserSerializer(request.user).data)


class ExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={(200, "application/json"): OpenApiResponse(description="Personal data export")}
    )
    def get(self, request):
        data = services.export_user_data(request.user)
        response = HttpResponse(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            content_type="application/json",
        )
        response["Content-Disposition"] = 'attachment; filename="undercut-export.json"'
        return response


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=s.DeleteAccountSerializer,
        responses={204: None, 400: s.ErrorSerializer, 403: s.ErrorSerializer},
    )
    def post(self, request):
        body = s.DeleteAccountSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            services.delete_account(request.user, body.validated_data["display_name"])
        except services.DemoLocked as exc:
            return _error(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except services.AccountError as exc:
            return _error(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoritesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=s.FavoritesSerializer)
    def get(self, request):
        return Response(_favorites_payload(request.user))


def _favorites_payload(user) -> dict:
    data = services.list_favorites(user)
    return s.FavoritesSerializer(
        {
            **data,
            "limits": {
                "drivers": services.MAX_FAVORITE_DRIVERS,
                "constructors": services.MAX_FAVORITE_CONSTRUCTORS,
            },
        }
    ).data


class _FavoriteTargetView(APIView):
    """PUT adds, DELETE removes; both are idempotent. Both return the current state."""

    permission_classes = [IsAuthenticated]
    kind: services.FavoriteKind

    @extend_schema(
        request=None,
        responses={200: s.FavoriteStateSerializer, 404: s.ErrorSerializer, 409: s.ErrorSerializer},
    )
    def put(self, request, slug: str):
        try:
            services.add_favorite(request.user, self.kind, slug)
        except services.NotFound as exc:
            return _error(exc.code, exc.message, status.HTTP_404_NOT_FOUND)
        except services.LimitReached as exc:
            return _error(exc.code, exc.message, status.HTTP_409_CONFLICT)
        return Response({"favorite": True})

    @extend_schema(request=None, responses={200: s.FavoriteStateSerializer})
    def delete(self, request, slug: str):
        services.remove_favorite(request.user, self.kind, slug)
        return Response({"favorite": False})


class FavoriteDriverView(_FavoriteTargetView):
    kind = "driver"


class FavoriteConstructorView(_FavoriteTargetView):
    kind = "constructor"

"""Thin read-only views: validate input, call a selector, serialise."""

from collections.abc import Callable
from typing import Any

from django.utils.cache import patch_cache_control
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.catalog.lookups import SessionHeader

from .. import selectors
from . import serializers

CACHE_SECONDS = 60
RESPONSES = {404: serializers.NotFoundSerializer}


class AnalyticsView(APIView):
    """Anonymous GET-only access to the analytics of one session of a round."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def respond(
        self,
        request,
        year: int,
        round_number: int,
        query_serializer: type[Serializer],
        response_serializer: type[Serializer],
        build: Callable[[SessionHeader, dict[str, Any]], dict[str, Any]],
    ) -> Response:
        query = query_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        try:
            header = selectors.load_header(year, round_number, params.get("session", "RACE"))
            body = build(header, params)
        except selectors.AnalyticsNotFound as exc:
            return Response(
                {"detail": exc.message, "analytics_available": exc.analytics_available},
                status=status.HTTP_404_NOT_FOUND,
            )
        response = Response(response_serializer(body).data)
        if header.is_final:
            patch_cache_control(response, public=True, max_age=CACHE_SECONDS)
        return response


class PositionsView(AnalyticsView):
    @extend_schema(
        tags=["analytics"],
        summary="Position of every driver at the end of every lap",
        parameters=[serializers.SessionQuerySerializer],
        responses={200: serializers.PositionsSerializer, **RESPONSES},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond(
            request,
            year,
            round,
            serializers.SessionQuerySerializer,
            serializers.PositionsSerializer,
            lambda header, _params: selectors.positions(header),
        )


class LapsView(AnalyticsView):
    @extend_schema(
        tags=["analytics"],
        summary="Lap times with sector times and per driver summary",
        parameters=[serializers.LapsQuerySerializer],
        responses={200: serializers.LapsSerializer, **RESPONSES},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond(
            request,
            year,
            round,
            serializers.LapsQuerySerializer,
            serializers.LapsSerializer,
            lambda header, params: selectors.laps(
                header, params.get("drivers", []), params["hide_slow"]
            ),
        )


class StintsView(AnalyticsView):
    @extend_schema(
        tags=["analytics"],
        summary="Tyre strategy per driver",
        parameters=[serializers.SessionQuerySerializer],
        responses={200: serializers.StintsSerializer, **RESPONSES},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond(
            request,
            year,
            round,
            serializers.SessionQuerySerializer,
            serializers.StintsSerializer,
            lambda header, _params: selectors.stints(header),
        )


class PitStopsView(AnalyticsView):
    @extend_schema(
        tags=["analytics"],
        summary="Pit stops and team ranking of the fastest stops",
        parameters=[serializers.SessionQuerySerializer],
        responses={200: serializers.PitStopsSerializer, **RESPONSES},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond(
            request,
            year,
            round,
            serializers.SessionQuerySerializer,
            serializers.PitStopsSerializer,
            lambda header, _params: selectors.pit_stops(header),
        )


class WeatherView(AnalyticsView):
    @extend_schema(
        tags=["analytics"],
        summary="Weather during the session (at most 120 points)",
        parameters=[serializers.SessionQuerySerializer],
        responses={200: serializers.WeatherSerializer, **RESPONSES},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond(
            request,
            year,
            round,
            serializers.SessionQuerySerializer,
            serializers.WeatherSerializer,
            lambda header, _params: selectors.weather(header),
        )


class RaceControlView(AnalyticsView):
    @extend_schema(
        tags=["analytics"],
        summary="Race control messages",
        parameters=[serializers.RaceControlQuerySerializer],
        responses={200: serializers.RaceControlSerializer, **RESPONSES},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond(
            request,
            year,
            round,
            serializers.RaceControlQuerySerializer,
            serializers.RaceControlSerializer,
            lambda header, params: selectors.race_control(header, params.get("category")),
        )

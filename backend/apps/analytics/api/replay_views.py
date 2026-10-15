"""Replay endpoints (FR-701): one compact document and the jump-to-lap helper."""

from collections.abc import Callable
from typing import Any

from django.utils.cache import patch_cache_control
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from apps.catalog.lookups import SessionHeader

from .. import replay, selectors
from . import replay_serializers as serializers
from .views import RESPONSES, AnalyticsView

REPLAY_CACHE_SECONDS = 300
BAD_REQUEST = OpenApiResponse(
    description="Invalid query parameter, for example step outside 1..30."
)


class ReplayBaseView(AnalyticsView):
    def respond_replay(
        self,
        request,
        year: int,
        round_number: int,
        query_serializer: type[Serializer],
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
        response = Response(body)  # already plain JSON types, see replay_serializers
        if header.is_final:
            patch_cache_control(response, public=True, max_age=REPLAY_CACHE_SECONDS)
        return response


class ReplayView(ReplayBaseView):
    @extend_schema(
        tags=["analytics"],
        summary="Compact race replay timeline sampled at a fixed step",
        description=(
            "Column encoded frames every `step` seconds from the start of lap 1. A frame value "
            "is the last known sample at or before its time. `pos`, `gap` and `int` are dense "
            "arrays aligned to `frames.t`; `lap`, `tyre`, `age` and `pit` are run encoded "
            "(`at` frame indexes, `v` values). Cacheable for finished sessions."
        ),
        parameters=[serializers.ReplayQuerySerializer],
        responses={
            200: serializers.ReplaySerializer,
            400: BAD_REQUEST,
            404: RESPONSES[404],
        },
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond_replay(
            request,
            year,
            round,
            serializers.ReplayQuerySerializer,
            lambda header, params: replay.replay(header, params["step"]),
        )


class ReplayLapsView(ReplayBaseView):
    @extend_schema(
        tags=["analytics"],
        summary="Jump-to-lap offsets: lap number to the leader's lap start time",
        parameters=[serializers.ReplayLapsQuerySerializer],
        responses={200: serializers.ReplayLapsSerializer, 404: RESPONSES[404]},
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        return self.respond_replay(
            request,
            year,
            round,
            serializers.ReplayLapsQuerySerializer,
            lambda header, _params: replay.lap_offsets(header),
        )

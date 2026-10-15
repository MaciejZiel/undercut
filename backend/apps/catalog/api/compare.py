"""Driver comparison (FR-405)."""

from collections.abc import Callable

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from .. import selectors
from ..models import Driver
from . import filters
from .serializers import CareerStatsSerializer, DriverRefSerializer
from .views import PublicDetailView, _validated

# --- Lap-time extension point ----------------------------------------------------------------
#
# Per-race lap-time comparison of team mates (same team, seasons from 2023) needs lap data that
# lives in the analytics module, and catalog must not import analytics models. The integration
# point is this module-level hook: analytics (or the project wiring) assigns a callable
#
#     provider(year: int, slug_a: str, slug_b: str) -> list[dict] | None
#
# that returns one dict per race, shaped like LapTimeRaceSerializer (round, name,
# a_median_lap_ms, b_median_lap_ms, delta_ms), or None when it has no lap data for that
# season. While the hook is unset the response carries `lap_times: null` and the reason below.

LapTimeProvider = Callable[[int, str, str], list[dict] | None]
LAP_TIME_PROVIDER: LapTimeProvider | None = None
REASON_NOT_INTEGRATED = "Lap-time analytics are not available (no lap-time provider registered)."
REASON_NO_DATA = "No lap-time data for this season."


def lap_time_comparison(
    year: int, slug_a: str, slug_b: str
) -> tuple[list[dict] | None, str | None]:
    """Return (races, reason); races is None and reason says why when there is no data."""
    if LAP_TIME_PROVIDER is None:
        return None, REASON_NOT_INTEGRATED
    races = LAP_TIME_PROVIDER(year, slug_a, slug_b)
    return (races, None) if races else (None, REASON_NO_DATA)


# --- Serializers -----------------------------------------------------------------------------


class CompareQuerySerializer(serializers.Serializer):
    a = serializers.SlugField(help_text="Slug of the first driver.")
    b = serializers.SlugField(help_text="Slug of the second driver.")
    season = serializers.IntegerField(
        required=False,
        min_value=filters.MIN_YEAR,
        max_value=filters.MAX_YEAR,
        help_text="Limit the head-to-head to this season.",
    )

    def validate(self, attrs):
        if attrs["a"] == attrs["b"]:
            raise serializers.ValidationError("Pick two different drivers.")
        return attrs


class CompareSideSerializer(serializers.Serializer):
    driver = DriverRefSerializer()
    stats = CareerStatsSerializer()


class AheadCountsSerializer(serializers.Serializer):
    a_ahead = serializers.IntegerField()
    b_ahead = serializers.IntegerField()


class RaceHeadToHeadSerializer(AheadCountsSerializer):
    both_finished = serializers.IntegerField(
        help_text="Races where both were classified and not level on position."
    )


class QualifyingHeadToHeadSerializer(AheadCountsSerializer):
    compared = serializers.IntegerField(
        help_text="Qualifying position from 1994, grid position before."
    )


class LapTimeRaceSerializer(serializers.Serializer):
    round = serializers.IntegerField()
    name = serializers.CharField()
    a_median_lap_ms = serializers.IntegerField(allow_null=True)
    b_median_lap_ms = serializers.IntegerField(allow_null=True)
    delta_ms = serializers.IntegerField(allow_null=True, help_text="a minus b.")


class TeammateSeasonSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    team_slug = serializers.CharField()
    races = serializers.IntegerField(help_text="Races both started for this team.")
    lap_times = LapTimeRaceSerializer(
        many=True, allow_null=True, help_text="Null when there is no lap data, see the reason."
    )
    lap_times_reason = serializers.CharField(allow_null=True)


class HeadToHeadSerializer(serializers.Serializer):
    races_together = serializers.IntegerField()
    same_team_races = serializers.IntegerField()
    race = RaceHeadToHeadSerializer()
    qualifying = QualifyingHeadToHeadSerializer()
    teammate_seasons = TeammateSeasonSerializer(many=True, help_text="Same team, from 2023.")


class CompareSerializer(serializers.Serializer):
    season = serializers.IntegerField(allow_null=True)
    a = CompareSideSerializer()
    b = CompareSideSerializer()
    head_to_head = HeadToHeadSerializer()


class CompareView(PublicDetailView):
    @extend_schema(
        tags=["drivers"],
        summary="Compare two drivers",
        parameters=[CompareQuerySerializer],
        responses=CompareSerializer,
    )
    def get(self, request):
        data = _validated(CompareQuerySerializer, request)
        a = get_object_or_404(Driver, slug=data["a"])
        b = get_object_or_404(Driver, slug=data["b"])
        body = selectors.compare_drivers(a, b, data.get("season"))
        for season in body["head_to_head"]["teammate_seasons"]:
            season["lap_times"], season["lap_times_reason"] = lap_time_comparison(
                season["year"], a.slug, b.slug
            )
        return Response(CompareSerializer(body).data)

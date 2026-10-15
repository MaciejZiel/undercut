from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import selectors
from .serializers import (
    ProgressQuerySerializer,
    ProgressSerializer,
    StandingsQuerySerializer,
    StandingsSerializer,
)


def _resolve_season(kind: str, year: int | None) -> tuple[int | None, int | None]:
    """Return (season_id, year); (None, None) when nothing is imported yet."""
    if year is None:
        latest = selectors.latest_position(kind)
        return (latest.season_id, latest.year) if latest else (None, None)
    season_id = selectors.find_season_id(year)
    if season_id is None:
        raise NotFound(f"Season {year} does not exist.")
    return season_id, year


class _KindMixin:
    kind: selectors.Kind
    permission_classes = [AllowAny]


class StandingsView(_KindMixin, APIView):
    @extend_schema(
        parameters=[StandingsQuerySerializer],
        responses=StandingsSerializer,
        summary="Championship standings after a round",
    )
    def get(self, request):
        params = StandingsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        season_id, year = _resolve_season(self.kind, params.validated_data.get("season"))
        if season_id is None:
            return Response({"season": None, "after_round": None, "rounds": [], "results": []})
        rounds = selectors.available_rounds(self.kind, season_id)
        after_round = params.validated_data.get("after_round")
        if after_round is None:
            after_round = rounds[-1] if rounds else None
        elif after_round not in rounds:
            raise NotFound(f"No standings for season {year} after round {after_round}.")
        rows = selectors.standings_rows(self.kind, season_id, after_round) if rounds else []
        body = {"season": year, "after_round": after_round, "rounds": rounds, "results": rows}
        return Response(StandingsSerializer(body).data)


class ProgressView(_KindMixin, APIView):
    @extend_schema(
        parameters=[ProgressQuerySerializer],
        responses=ProgressSerializer,
        summary="Cumulative points and position per round",
    )
    def get(self, request):
        params = ProgressQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        season_id, year = _resolve_season(self.kind, params.validated_data.get("season"))
        if season_id is None:
            return Response({"season": None, "rounds": [], "series": []})
        data = selectors.points_progression(self.kind, season_id, params.validated_data["top"])
        return Response(ProgressSerializer({"season": year, **data}).data)


class DriverStandingsView(StandingsView):
    kind = "drivers"


class ConstructorStandingsView(StandingsView):
    kind = "constructors"


class DriverProgressView(ProgressView):
    kind = "drivers"


class ConstructorProgressView(ProgressView):
    kind = "constructors"

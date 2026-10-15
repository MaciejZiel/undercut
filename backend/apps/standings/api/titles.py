"""Title race (FR-305): who can still win the drivers' championship."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import selectors
from .serializers import EntitySerializer

_DECIMAL = {"max_digits": 6, "decimal_places": 2, "coerce_to_string": False}


class TitleRaceQuerySerializer(serializers.Serializer):
    season = serializers.IntegerField(
        required=False,
        min_value=1950,
        max_value=2200,
        help_text="Season year (default: latest season with standings).",
    )


class ContenderSerializer(serializers.Serializer):
    position = serializers.IntegerField(allow_null=True)
    entity = EntitySerializer()
    points = serializers.DecimalField(**_DECIMAL)
    max_points = serializers.DecimalField(
        **_DECIMAL, help_text="Current points plus everything left in remaining races and sprints."
    )
    gap_to_leader = serializers.DecimalField(**_DECIMAL)
    tie_break_needed = serializers.BooleanField(
        help_text="Can at best equal the best rival's points; the countback would decide."
    )


class TitleRaceSerializer(serializers.Serializer):
    season = serializers.IntegerField(allow_null=True)
    after_round = serializers.IntegerField(allow_null=True)
    rounds_remaining = serializers.IntegerField(allow_null=True)
    sprints_remaining = serializers.IntegerField(allow_null=True)
    max_points_available = serializers.DecimalField(
        **_DECIMAL, allow_null=True, help_text="Most a single driver can still score."
    )
    fastest_lap_point = serializers.BooleanField(allow_null=True)
    decided = serializers.BooleanField()
    champion = EntitySerializer(allow_null=True)
    decided_in_round = serializers.IntegerField(allow_null=True)
    message = serializers.CharField(allow_null=True, help_text='"Champion decided in round N".')
    contenders = ContenderSerializer(many=True, help_text="Drivers who can still win the title.")
    eliminated = serializers.IntegerField(help_text="Drivers in the table without a chance.")


class TitleRaceView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["standings"],
        parameters=[TitleRaceQuerySerializer],
        responses=TitleRaceSerializer,
        summary="Mathematical title race",
    )
    def get(self, request):
        params = TitleRaceQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        year = params.validated_data.get("season")
        if year is None:
            latest = selectors.latest_position("drivers")
            season_id = latest.season_id if latest else None
        else:
            season_id = selectors.find_season_id(year)
            if season_id is None:
                raise NotFound(f"Season {year} does not exist.")
        race = selectors.title_race(season_id) if season_id is not None else None
        if race is None:
            body = {
                "season": year,
                "after_round": None,
                "rounds_remaining": None,
                "sprints_remaining": None,
                "max_points_available": None,
                "fastest_lap_point": None,
                "decided": False,
                "champion": None,
                "decided_in_round": None,
                "message": None,
                "contenders": [],
                "eliminated": 0,
            }
            return Response(TitleRaceSerializer(body).data)
        decided_in = race["decided_in_round"]
        body = {
            "season": race["year"],
            "after_round": race["after_round"],
            "rounds_remaining": race["rounds_remaining"],
            "sprints_remaining": race["sprints_remaining"],
            "max_points_available": race["max_available"],
            "fastest_lap_point": race["fastest_lap_point"],
            "decided": race["champion"] is not None,
            "champion": race["champion"],
            "decided_in_round": decided_in,
            "message": None if decided_in is None else f"Champion decided in round {decided_in}",
            "contenders": race["contenders"],
            "eliminated": race["eliminated"],
        }
        return Response(TitleRaceSerializer(body).data)

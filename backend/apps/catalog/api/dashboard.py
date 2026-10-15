"""Home page data (FR-105, FR-106): one request, everything null-safe."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from .. import selectors
from .calendar import CalendarEntrySerializer
from .serializers import CircuitRefSerializer, DriverRefSerializer, TeamRefSerializer
from .views import PublicDetailView


class DashboardNextRaceSerializer(CalendarEntrySerializer):
    year = serializers.IntegerField()


class PodiumEntrySerializer(serializers.Serializer):
    position = serializers.IntegerField()
    driver = DriverRefSerializer()
    team = TeamRefSerializer(help_text="Team on race day with its season colour.")


class FastestLapSerializer(serializers.Serializer):
    driver = DriverRefSerializer()
    team = TeamRefSerializer()
    time_ms = serializers.IntegerField(allow_null=True)


class LastRaceSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    date = serializers.DateField()
    circuit = CircuitRefSerializer()
    podium = PodiumEntrySerializer(many=True)
    fastest_lap = FastestLapSerializer(allow_null=True, help_text="Null when unknown.")


class StandingsEntrySerializer(serializers.Serializer):
    position = serializers.IntegerField(allow_null=True)
    slug = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    color = serializers.CharField(
        allow_null=True, help_text="Team colour: the constructor itself, or the driver's team."
    )
    team_name = serializers.CharField(allow_null=True, help_text="Drivers only: their team.")
    points = serializers.DecimalField(max_digits=6, decimal_places=2, coerce_to_string=False)
    wins = serializers.IntegerField()


class TopStandingsSerializer(serializers.Serializer):
    season = serializers.IntegerField(allow_null=True)
    after_round = serializers.IntegerField(allow_null=True)
    entries = StandingsEntrySerializer(many=True, help_text="Top five.")


class ThisDaySerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField(allow_null=True)
    race = serializers.CharField()
    date = serializers.DateField()
    driver = DriverRefSerializer(help_text="The winner.")
    team = TeamRefSerializer()


class CountsSerializer(serializers.Serializer):
    seasons = serializers.IntegerField()
    races = serializers.IntegerField(help_text="Rounds held so far, cancelled excluded.")
    drivers = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    next_race = DashboardNextRaceSerializer(allow_null=True)
    last_race = LastRaceSerializer(allow_null=True)
    driver_standings = TopStandingsSerializer()
    constructor_standings = TopStandingsSerializer()
    this_day_in_f1 = ThisDaySerializer(
        allow_null=True, help_text="A race won on today's day and month in an earlier year."
    )
    counts = CountsSerializer()


class DashboardView(PublicDetailView):
    @extend_schema(tags=["dashboard"], summary="Home page data", responses=DashboardSerializer)
    def get(self, request):
        return Response(DashboardSerializer(selectors.dashboard()).data)

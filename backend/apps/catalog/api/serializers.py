"""Response serializers of the public catalog API.

Missing data is serialised as null, never as zero. Blank strings are turned into null too.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class NullableCharField(serializers.CharField):
    """Blank strings mean "no data" and are shown as null."""

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        return super().to_representation(value) if value not in (None, "") else None


class TeamRefSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    color = serializers.CharField(allow_null=True, help_text="#rrggbb or null (neutral colour).")


class DriverRefSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    number = serializers.IntegerField(allow_null=True)


class CircuitRefSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    country = serializers.CharField(allow_null=True)


class RoundLinkSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField()
    name = serializers.CharField()


class CareerStatsSerializer(serializers.Serializer):
    """Career totals; all values are null when the module has no race results.

    ``titles`` are championships won (constructors from 1958), see the standings module.
    """

    starts = serializers.IntegerField(allow_null=True)
    wins = serializers.IntegerField(allow_null=True)
    podiums = serializers.IntegerField(allow_null=True)
    poles = serializers.IntegerField(
        allow_null=True,
        help_text="Grid position 1 before 1994, qualifying position 1 from 1994.",
    )
    fastest_laps = serializers.IntegerField(allow_null=True)
    points = serializers.FloatField(allow_null=True, help_text="Race and sprint points.")
    titles = serializers.IntegerField(allow_null=True, default=None)


# --- Drivers ---------------------------------------------------------------------------------


class DriverListSerializer(serializers.Serializer):
    """Row of the driver list; ``titles`` is the number of world championships.

    ``id`` is exposed because the prediction API identifies drivers by it.
    """

    id = serializers.IntegerField()
    slug = serializers.CharField()
    given_name = serializers.CharField()
    family_name = serializers.CharField()
    code = NullableCharField()
    number = serializers.IntegerField(source="permanent_number", allow_null=True)
    nationality = NullableCharField()
    starts = serializers.IntegerField()
    wins = serializers.IntegerField()
    titles = serializers.IntegerField()
    team = serializers.SerializerMethodField(help_text="Current or last team on race day.")

    @extend_schema_field(TeamRefSerializer(allow_null=True))
    def get_team(self, obj):
        if obj.last_constructor_slug is None:
            return None
        return {
            "slug": obj.last_constructor_slug,
            "name": obj.last_constructor_name,
            "color": obj.last_constructor_color,
        }


class DriverSeasonSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    teams = TeamRefSerializer(many=True, help_text="Teams on race day (several after a transfer).")
    points = serializers.FloatField(allow_null=True)
    wins = serializers.IntegerField()
    championship_position = serializers.IntegerField(
        allow_null=True,
        help_text="Position in the newest table of the season (final once the season is over).",
    )


class DriverResultSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField(allow_null=True)
    round_name = serializers.CharField()
    date = serializers.DateField()
    team = TeamRefSerializer()
    grid = serializers.IntegerField(allow_null=True)
    position = serializers.IntegerField(allow_null=True)
    position_text = serializers.CharField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    points = serializers.FloatField(allow_null=True)


class DriverDetailSerializer(serializers.Serializer):
    """Driver page."""

    slug = serializers.CharField()
    given_name = serializers.CharField()
    family_name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    number = serializers.IntegerField(allow_null=True)
    nationality = serializers.CharField(allow_null=True)
    date_of_birth = serializers.DateField(allow_null=True)
    team = TeamRefSerializer(allow_null=True, help_text="Current or last team on race day.")
    stats = CareerStatsSerializer()
    seasons = DriverSeasonSerializer(many=True)
    last_results = DriverResultSerializer(many=True)


# --- Constructors ----------------------------------------------------------------------------


class ConstructorListSerializer(serializers.Serializer):
    """Row of the constructor list; ``titles`` counts constructors' championships (from 1958)."""

    slug = serializers.CharField()
    name = serializers.CharField()
    nationality = NullableCharField()
    starts = serializers.IntegerField()
    wins = serializers.IntegerField()
    titles = serializers.IntegerField()


class SeasonDriverSerializer(DriverRefSerializer):
    pass


class ConstructorSeasonRowSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    color = serializers.CharField(allow_null=True)
    points = serializers.FloatField(allow_null=True)
    wins = serializers.IntegerField()
    championship_position = serializers.IntegerField(
        allow_null=True,
        help_text="Position in the newest table of the season (final once the season is over).",
    )
    drivers = SeasonDriverSerializer(many=True)


class ConstructorDetailSerializer(serializers.Serializer):
    """Constructor page."""

    slug = serializers.CharField()
    name = serializers.CharField()
    nationality = serializers.CharField(allow_null=True)
    stats = CareerStatsSerializer()
    seasons = ConstructorSeasonRowSerializer(many=True)
    current_season = serializers.IntegerField(allow_null=True, help_text="Latest season raced.")
    current_drivers = SeasonDriverSerializer(many=True)


# --- Circuits --------------------------------------------------------------------------------


class CircuitListSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    locality = NullableCharField()
    country = NullableCharField()
    gp_count = serializers.IntegerField(help_text="Grands Prix held so far, cancelled excluded.")
    last_gp_date = serializers.DateField(allow_null=True)


class CircuitWinnerSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField(allow_null=True)
    round_name = serializers.CharField()
    date = serializers.DateField()
    driver = DriverRefSerializer()
    team = TeamRefSerializer()


class MostWinsDriverSerializer(DriverRefSerializer):
    wins = serializers.IntegerField()


class MostWinsTeamSerializer(TeamRefSerializer):
    wins = serializers.IntegerField()


class CircuitOutlineSerializer(serializers.Serializer):
    width = serializers.IntegerField(help_text="SVG viewBox width (the outline fits 0..1000).")
    height = serializers.IntegerField()
    points = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField(), min_length=2, max_length=2),
        help_text="Closed racing line, [x, y] pairs; y grows downwards (SVG).",
    )


class CircuitDetailSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    locality = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    lat = serializers.FloatField(allow_null=True)
    lng = serializers.FloatField(allow_null=True)
    timezone = serializers.CharField(allow_null=True)
    length_m = serializers.IntegerField(allow_null=True)
    length_is_estimate = serializers.BooleanField(
        help_text="True when the length was measured on the outline (rounded to 100 m)."
    )
    lap_record_ms = serializers.IntegerField(
        allow_null=True, help_text="Fastest race lap on record."
    )
    lap_record_driver = serializers.CharField(allow_null=True)
    lap_record_year = serializers.IntegerField(allow_null=True)
    outline = CircuitOutlineSerializer(allow_null=True)
    gp_count = serializers.IntegerField()
    last_gp_date = serializers.DateField(allow_null=True)
    winners = CircuitWinnerSerializer(many=True, help_text="Newest first.")
    most_wins_drivers = MostWinsDriverSerializer(many=True)
    most_wins_teams = MostWinsTeamSerializer(many=True)


# --- Seasons and rounds ----------------------------------------------------------------------


class SeasonListSerializer(serializers.Serializer):
    """Row of the season list; champions are null until the season is finished."""

    year = serializers.IntegerField()
    name = NullableCharField()
    rounds_count = serializers.IntegerField(help_text="All rounds, cancelled included.")
    cancelled_rounds = serializers.IntegerField()
    sprint_rounds = serializers.IntegerField()
    driver_champion = DriverRefSerializer(allow_null=True, read_only=True, default=None)
    constructor_champion = TeamRefSerializer(allow_null=True, read_only=True, default=None)


class RoundWinnerSerializer(serializers.Serializer):
    driver = DriverRefSerializer()
    team = TeamRefSerializer()


class CalendarRoundSerializer(serializers.Serializer):
    round = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    date = serializers.DateField()
    is_cancelled = serializers.BooleanField()
    has_sprint = serializers.BooleanField()
    circuit = CircuitRefSerializer()
    winner = RoundWinnerSerializer(allow_null=True, help_text="Null for upcoming rounds.")


class SeasonDetailSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    sprint_rounds = serializers.IntegerField()
    rounds = CalendarRoundSerializer(many=True)


class RoundCircuitSerializer(CircuitRefSerializer):
    locality = serializers.CharField(allow_null=True)
    length_m = serializers.IntegerField(allow_null=True)


class RoundSessionSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="FP1, FP2, FP3, SQ, SPRINT, Q or RACE.")
    status = serializers.CharField()
    start_utc = serializers.DateTimeField(allow_null=True)
    has_results = serializers.BooleanField()


class RoundDetailSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField()
    name = serializers.CharField()
    date = serializers.DateField()
    is_cancelled = serializers.BooleanField()
    scheduled_laps = serializers.IntegerField(allow_null=True)
    circuit = RoundCircuitSerializer()
    sessions = RoundSessionSerializer(many=True, help_text="Only sessions that exist.")
    previous_round = RoundLinkSerializer(allow_null=True)
    next_round = RoundLinkSerializer(allow_null=True)


class RaceResultSerializer(serializers.Serializer):
    position = serializers.IntegerField(allow_null=True)
    position_text = serializers.CharField(allow_null=True, help_text="For example R, D or W.")
    driver = DriverRefSerializer()
    team = TeamRefSerializer(help_text="Team on race day.")
    grid = serializers.IntegerField(allow_null=True)
    laps = serializers.IntegerField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    time_ms = serializers.IntegerField(allow_null=True)
    best_lap_ms = serializers.IntegerField(allow_null=True)
    points = serializers.FloatField(allow_null=True)
    fastest_lap = serializers.BooleanField(
        allow_null=True, help_text="True for the fastest lap, null when there is no data."
    )
    position_change = serializers.IntegerField(
        allow_null=True, help_text="Grid minus finish; positive means places gained."
    )


class QualifyingResultSerializer(serializers.Serializer):
    position = serializers.IntegerField(allow_null=True)
    driver = DriverRefSerializer()
    team = TeamRefSerializer()
    q1_ms = serializers.IntegerField(allow_null=True)
    q2_ms = serializers.IntegerField(allow_null=True)
    q3_ms = serializers.IntegerField(allow_null=True)
    eliminated_in = serializers.ChoiceField(choices=["Q1", "Q2"], allow_null=True)


class ResultsSessionSerializer(serializers.Serializer):
    type = serializers.CharField()
    status = serializers.CharField()


class RaceSessionResultsSerializer(serializers.Serializer):
    """Race or sprint results."""

    year = serializers.IntegerField()
    round = serializers.IntegerField()
    session = ResultsSessionSerializer()
    results = RaceResultSerializer(many=True)


class QualifyingSessionResultsSerializer(serializers.Serializer):
    """Qualifying results."""

    year = serializers.IntegerField()
    round = serializers.IntegerField()
    session = ResultsSessionSerializer()
    results = QualifyingResultSerializer(many=True)


# --- Search ----------------------------------------------------------------------------------


class SearchDriverSerializer(DriverRefSerializer):
    nationality = serializers.CharField(allow_null=True)


class SearchConstructorSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    nationality = serializers.CharField(allow_null=True)


class SearchRoundSerializer(RoundLinkSerializer):
    date = serializers.DateField()


class SearchSerializer(serializers.Serializer):
    drivers = SearchDriverSerializer(many=True)
    constructors = SearchConstructorSerializer(many=True)
    circuits = CircuitRefSerializer(many=True)
    rounds = SearchRoundSerializer(many=True)

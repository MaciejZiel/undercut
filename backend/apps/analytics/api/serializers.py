"""Explicit serializers of the analytics read API (query parameters and responses)."""

from rest_framework import serializers

SESSION_CHOICES = ["RACE", "SPRINT", "Q"]
COMPOUND_CHOICES = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", "UNKNOWN"]


# --- Query parameters ------------------------------------------------------------------------


class SessionQuerySerializer(serializers.Serializer):
    session = serializers.ChoiceField(choices=SESSION_CHOICES, default="RACE", required=False)


class LapsQuerySerializer(SessionQuerySerializer):
    drivers = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma separated driver codes, for example VER,NOR. Default: all drivers.",
    )
    hide_slow = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Exclude pit-out laps, in laps and laps under SC/VSC (default true).",
    )

    def validate_drivers(self, value: str) -> list[str]:
        codes = [part.strip().upper() for part in value.split(",") if part.strip()]
        if len(codes) > 30 or any(not (c.isalnum() and len(c) <= 3) for c in codes):
            raise serializers.ValidationError("Use up to 30 driver codes of at most 3 letters.")
        return codes


class RaceControlQuerySerializer(SessionQuerySerializer):
    category = serializers.CharField(
        required=False, max_length=40, help_text="Category, for example Flag or SafetyCar."
    )


# --- Responses -------------------------------------------------------------------------------


class NotFoundSerializer(serializers.Serializer):
    detail = serializers.CharField()
    analytics_available = serializers.BooleanField(
        help_text="Whether detailed analytics exist for the season (2023 onwards)."
    )


class SessionHeaderSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    round = serializers.IntegerField()
    round_name = serializers.CharField()
    type = serializers.ChoiceField(choices=SESSION_CHOICES)
    status = serializers.CharField()


class DriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    code = serializers.CharField()
    full_name = serializers.CharField()
    constructor_id = serializers.IntegerField()
    constructor_name = serializers.CharField()
    color_hex = serializers.CharField(allow_null=True, help_text="#rrggbb, null = neutral colour.")


class NeutralisationSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["SC", "VSC"])
    start_lap = serializers.IntegerField()
    end_lap = serializers.IntegerField(help_text="Inclusive.")


def _int_list(**kwargs) -> serializers.ListField:
    return serializers.ListField(child=serializers.IntegerField(allow_null=True), **kwargs)


# positions


class PositionsDriverSerializer(DriverSerializer):
    positions = _int_list(help_text="Position at the end of each lap, aligned to `laps`.")
    pit_laps = _int_list(help_text="Lap numbers with a pit stop.")


class PositionsSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    laps = serializers.ListField(child=serializers.IntegerField())
    drivers = PositionsDriverSerializer(many=True)
    neutralisations = NeutralisationSerializer(many=True)


# laps


class LapSummarySerializer(serializers.Serializer):
    count = serializers.IntegerField()
    best_ms = serializers.IntegerField(allow_null=True)
    median_ms = serializers.FloatField(allow_null=True)
    stdev_ms = serializers.FloatField(allow_null=True)


class LapsDriverSerializer(DriverSerializer):
    lap_numbers = _int_list()
    duration_ms = _int_list(help_text="Aligned to lap_numbers.")
    sector1_ms = _int_list()
    sector2_ms = _int_list()
    sector3_ms = _int_list()
    summary = LapSummarySerializer()


class LapsSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    hide_slow = serializers.BooleanField()
    drivers = LapsDriverSerializer(many=True)
    neutralisations = NeutralisationSerializer(many=True)


# stints


class StintSerializer(serializers.Serializer):
    stint_number = serializers.IntegerField()
    compound = serializers.ChoiceField(choices=COMPOUND_CHOICES)
    compound_letter = serializers.ChoiceField(choices=["S", "M", "H", "I", "W", "?"])
    lap_start = serializers.IntegerField(allow_null=True)
    lap_end = serializers.IntegerField(allow_null=True)
    laps = serializers.IntegerField(allow_null=True, help_text="Stint length in laps.")
    tyre_age_at_start = serializers.IntegerField(allow_null=True)


class StintsDriverSerializer(DriverSerializer):
    position = serializers.IntegerField(allow_null=True, help_text="Final classification.")
    stints = StintSerializer(many=True)


class StintsSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    drivers = StintsDriverSerializer(many=True)


# pit stops


class PitStopSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    driver_code = serializers.CharField()
    constructor_id = serializers.IntegerField()
    constructor_name = serializers.CharField()
    color_hex = serializers.CharField(allow_null=True)
    lap = serializers.IntegerField(allow_null=True)
    stop_ms = serializers.IntegerField(allow_null=True, help_text="Stationary time.")
    lane_ms = serializers.IntegerField(allow_null=True, help_text="Pit lane time.")
    compound_from = serializers.CharField(allow_null=True, help_text="Compound before the stop.")
    compound_to = serializers.CharField(allow_null=True, help_text="Compound after the stop.")


class PitRankingSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    constructor_id = serializers.IntegerField()
    constructor_name = serializers.CharField()
    color_hex = serializers.CharField(allow_null=True)
    driver_code = serializers.CharField()
    lap = serializers.IntegerField(allow_null=True)
    duration_ms = serializers.IntegerField(help_text="Value of the method used.")


class PitStopsSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    method = serializers.ChoiceField(
        choices=["stop_duration", "lane_duration"], help_text="Which duration ranks the teams."
    )
    stops = PitStopSerializer(many=True)
    ranking = PitRankingSerializer(many=True)


# weather


class WeatherSampleSerializer(serializers.Serializer):
    ts = serializers.DateTimeField()
    air_temperature = serializers.FloatField(allow_null=True)
    track_temperature = serializers.FloatField(allow_null=True)
    humidity = serializers.FloatField(allow_null=True)
    pressure = serializers.FloatField(allow_null=True)
    wind_speed = serializers.FloatField(allow_null=True)
    wind_direction = serializers.IntegerField(allow_null=True)
    rainfall = serializers.BooleanField()


class WeatherSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    total_samples = serializers.IntegerField(help_text="Samples stored before downsampling.")
    samples = WeatherSampleSerializer(many=True)


# race control


class RaceControlMessageSerializer(serializers.Serializer):
    ts = serializers.DateTimeField()
    lap_number = serializers.IntegerField(allow_null=True)
    category = serializers.CharField(allow_blank=True)
    flag = serializers.CharField(allow_blank=True)
    scope = serializers.CharField(allow_blank=True)
    sector = serializers.IntegerField(allow_null=True)
    driver_code = serializers.CharField(allow_null=True)
    message = serializers.CharField()


class RaceControlSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    categories = serializers.ListField(child=serializers.CharField())
    messages = RaceControlMessageSerializer(many=True)

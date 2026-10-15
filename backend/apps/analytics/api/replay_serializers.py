"""Schema of the replay API. The views return plain dicts (a 30k value payload is not run
through serializer fields, that would dominate the response time); these classes describe it."""

from rest_framework import serializers

from apps.analytics import replay

from .serializers import SessionHeaderSerializer

REPLAY_SESSION_CHOICES = ["RACE", "SPRINT"]


class ReplayQuerySerializer(serializers.Serializer):
    session = serializers.ChoiceField(
        choices=REPLAY_SESSION_CHOICES, default="RACE", required=False
    )
    step = serializers.IntegerField(
        min_value=replay.MIN_STEP,
        max_value=replay.MAX_STEP,
        default=replay.DEFAULT_STEP,
        required=False,
        help_text="Seconds between frames (1 to 30).",
    )


class ReplayLapsQuerySerializer(serializers.Serializer):
    session = serializers.ChoiceField(
        choices=REPLAY_SESSION_CHOICES, default="RACE", required=False
    )


class ReplaySessionSerializer(SessionHeaderSerializer):
    start = serializers.DateTimeField(help_text="Start of lap 1, t = 0.")
    end = serializers.DateTimeField()
    laps = serializers.IntegerField()
    duration_s = serializers.FloatField()


class ReplayDriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    code = serializers.CharField()
    full_name = serializers.CharField()
    constructor_name = serializers.CharField()
    color_hex = serializers.CharField(allow_null=True, help_text="#rrggbb, null = neutral.")
    retired_t = serializers.FloatField(
        allow_null=True,
        help_text="Start (seconds) of the lap the driver did not complete; null = classified.",
    )


class RunsSerializer(serializers.Serializer):
    at = serializers.ListField(
        child=serializers.IntegerField(), help_text="Frame indexes where the value changes."
    )
    v = serializers.ListField(
        child=serializers.JSONField(allow_null=True),
        help_text="Value from that frame index until the next entry.",
    )


class ReplayDriverFramesSerializer(serializers.Serializer):
    pos = serializers.ListField(
        child=serializers.IntegerField(allow_null=True), help_text="Position per frame."
    )
    gap = serializers.ListField(
        child=serializers.JSONField(allow_null=True),
        help_text="Gap to the leader per frame: milliseconds, text such as '+1 LAP', or null.",
    )
    int = serializers.ListField(
        child=serializers.JSONField(allow_null=True),
        help_text="Interval to the car ahead per frame: milliseconds, text or null.",
    )
    lap = RunsSerializer(help_text="Current lap number, run encoded.")
    tyre = RunsSerializer(help_text="Compound, run encoded (null without stint data).")
    age = RunsSerializer(help_text="Tyre age in laps, run encoded.")
    pit = RunsSerializer(help_text="1 while inside the pit lane window, else 0; run encoded.")


class ReplayFramesSerializer(serializers.Serializer):
    step_s = serializers.IntegerField()
    count = serializers.IntegerField()
    t = serializers.ListField(
        child=serializers.IntegerField(), help_text="Seconds from the start, one per frame."
    )
    drivers = ReplayDriverFramesSerializer(many=True, help_text="Aligned to `drivers`.")


class ReplayEventSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=["start", "pit", "safety_car", "vsc", "red_flag", "chequered"]
    )
    t = serializers.FloatField()
    lap = serializers.IntegerField()
    label = serializers.CharField()
    driver = serializers.CharField(allow_null=True, help_text="Driver code for pit stops.")
    end_t = serializers.FloatField(allow_null=True, help_text="End of SC/VSC periods.")
    end_lap = serializers.IntegerField(allow_null=True)


class ReplaySerializer(serializers.Serializer):
    session = ReplaySessionSerializer()
    drivers = ReplayDriverSerializer(many=True)
    frames = ReplayFramesSerializer()
    events = ReplayEventSerializer(many=True)


class ReplayLapOffsetSerializer(serializers.Serializer):
    lap = serializers.IntegerField()
    t = serializers.FloatField(help_text="Seconds from the start to the leader's lap start.")


class ReplayLapsSerializer(serializers.Serializer):
    session = SessionHeaderSerializer()
    total_laps = serializers.IntegerField()
    duration_s = serializers.FloatField()
    laps = ReplayLapOffsetSerializer(many=True)

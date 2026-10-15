from rest_framework import serializers


class EntitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    nationality = serializers.CharField(allow_null=True)


class StandingRowSerializer(serializers.Serializer):
    position = serializers.IntegerField(allow_null=True)
    position_text = serializers.CharField()
    entity = EntitySerializer()
    points = serializers.DecimalField(max_digits=6, decimal_places=2, coerce_to_string=False)
    wins = serializers.IntegerField()
    podiums = serializers.IntegerField()
    gap_to_leader = serializers.DecimalField(max_digits=6, decimal_places=2, coerce_to_string=False)


class StandingsSerializer(serializers.Serializer):
    season = serializers.IntegerField(allow_null=True, help_text="Season year.")
    after_round = serializers.IntegerField(allow_null=True)
    rounds = serializers.ListField(
        child=serializers.IntegerField(), help_text="Rounds that have a table for this season."
    )
    results = StandingRowSerializer(many=True)


class ProgressSeriesSerializer(serializers.Serializer):
    entity = EntitySerializer()
    points = serializers.ListField(
        child=serializers.DecimalField(
            max_digits=6, decimal_places=2, coerce_to_string=False, allow_null=True
        ),
        help_text="Cumulative points per round, aligned to `rounds`.",
    )
    positions = serializers.ListField(
        child=serializers.IntegerField(allow_null=True),
        help_text="Championship position per round, aligned to `rounds`.",
    )


class ProgressSerializer(serializers.Serializer):
    season = serializers.IntegerField(allow_null=True)
    rounds = serializers.ListField(child=serializers.IntegerField())
    series = ProgressSeriesSerializer(many=True)


class StandingsQuerySerializer(serializers.Serializer):
    season = serializers.IntegerField(
        required=False, min_value=1950, max_value=2200, help_text="Season year (default: latest)."
    )
    after_round = serializers.IntegerField(
        required=False, min_value=1, max_value=100, help_text="Table after this round."
    )


class ProgressQuerySerializer(serializers.Serializer):
    season = serializers.IntegerField(
        required=False, min_value=1950, max_value=2200, help_text="Season year (default: latest)."
    )
    top = serializers.IntegerField(
        required=False, min_value=1, max_value=50, default=5, help_text="Entries to return."
    )

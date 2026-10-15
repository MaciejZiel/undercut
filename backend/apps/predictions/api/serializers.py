from rest_framework import serializers


class PickDriverSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)


class PredictionRoundSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    year = serializers.IntegerField()
    round = serializers.IntegerField()
    name = serializers.CharField()


class PickInputSerializer(serializers.Serializer):
    p1 = serializers.IntegerField(min_value=1, help_text="Driver id for P1")
    p2 = serializers.IntegerField(min_value=1, help_text="Driver id for P2")
    p3 = serializers.IntegerField(min_value=1, help_text="Driver id for P3")
    pole = serializers.IntegerField(min_value=1, help_text="Driver id for pole position")
    fastest_lap = serializers.IntegerField(min_value=1, help_text="Driver id for fastest lap")

    def validate(self, attrs):
        if len({attrs["p1"], attrs["p2"], attrs["p3"]}) != 3:
            raise serializers.ValidationError("A driver can appear only once on the podium.")
        return attrs


class PickSerializer(serializers.Serializer):
    p1 = PickDriverSerializer(allow_null=True)
    p2 = PickDriverSerializer(allow_null=True)
    p3 = PickDriverSerializer(allow_null=True)
    pole = PickDriverSerializer(allow_null=True)
    fastest_lap = PickDriverSerializer(allow_null=True)


class MyPickSerializer(PickSerializer):
    points = serializers.IntegerField(allow_null=True)
    breakdown = serializers.DictField()
    updated_at = serializers.DateTimeField()


class RoundStateSerializer(serializers.Serializer):
    round = PredictionRoundSerializer()
    status = serializers.ChoiceField(choices=["open", "closed", "unavailable"])
    closes_at = serializers.DateTimeField(allow_null=True)
    my_pick = MyPickSerializer(allow_null=True)


class HistoryRowSerializer(serializers.Serializer):
    round = PredictionRoundSerializer(allow_null=True)
    pick = PickSerializer()
    result = PickSerializer(allow_null=True)
    points = serializers.IntegerField(allow_null=True)
    breakdown = serializers.DictField()


class LeaderboardQuerySerializer(serializers.Serializer):
    season = serializers.IntegerField(required=False, min_value=1900)
    round = serializers.IntegerField(required=False, min_value=1)
    league = serializers.CharField(required=False, max_length=16)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=50)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)

    def validate(self, attrs):
        if "round" in attrs and "season" not in attrs:
            raise serializers.ValidationError({"round": "Requires the season parameter."})
        return attrs


class LeaderboardRowSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    points = serializers.IntegerField()
    exact_hits = serializers.IntegerField()
    pole_hits = serializers.IntegerField()
    exact_podiums = serializers.IntegerField()
    predictions = serializers.IntegerField()


class LeaderboardSerializer(serializers.Serializer):
    season = serializers.IntegerField(allow_null=True)
    round = serializers.IntegerField(allow_null=True)
    count = serializers.IntegerField()
    results = LeaderboardRowSerializer(many=True)


class LeagueCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)


class LeagueJoinSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16)


class LeagueSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    invite_code = serializers.CharField()
    is_owner = serializers.BooleanField()
    member_count = serializers.IntegerField()


class LeagueMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    joined_at = serializers.DateTimeField()


class LeagueDetailSerializer(serializers.Serializer):
    name = serializers.CharField()
    invite_code = serializers.CharField()
    owner_id = serializers.IntegerField(allow_null=True)
    is_owner = serializers.BooleanField()
    member_count = serializers.IntegerField()
    max_members = serializers.IntegerField()
    members = LeagueMemberSerializer(many=True)


class MemberPickSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    pick = PickSerializer()
    points = serializers.IntegerField(allow_null=True)
    breakdown = serializers.DictField()


class StatEntrySerializer(serializers.Serializer):
    driver = PickDriverSerializer(allow_null=True)
    count = serializers.IntegerField()
    percent = serializers.FloatField()


class PickStatsSerializer(serializers.Serializer):
    round = PredictionRoundSerializer()
    total = serializers.IntegerField()
    slots = serializers.DictField(child=StatEntrySerializer(many=True))


class PredictionErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()

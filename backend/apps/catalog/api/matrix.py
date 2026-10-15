"""Season matrix (FR-304): drivers x rounds."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from .. import selectors
from ..models import Season
from .serializers import TeamRefSerializer
from .views import PublicDetailView


class MatrixRoundSerializer(serializers.Serializer):
    round = serializers.IntegerField()
    name = serializers.CharField()
    date = serializers.DateField()
    country = serializers.CharField(allow_null=True)


class MatrixCellSerializer(serializers.Serializer):
    position = serializers.IntegerField(
        allow_null=True, help_text="Classified finishing position, null when not classified."
    )
    category = serializers.ChoiceField(
        choices=["win", "podium", "points", "no_points", "dnf"],
        help_text="podium is P2-P3; dnf covers retired, disqualified and not classified.",
    )


class MatrixDriverSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    position = serializers.IntegerField(
        allow_null=True, help_text="Championship position in the newest table."
    )
    points = serializers.FloatField(help_text="Race points scored in the listed rounds.")
    team = TeamRefSerializer(help_text="Team in the driver's latest race of the season.")
    cells = serializers.ListField(
        child=MatrixCellSerializer(allow_null=True),
        help_text="Aligned to `rounds`; a null item means the driver did not take part.",
    )


class MatrixSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    rounds = MatrixRoundSerializer(many=True)
    drivers = MatrixDriverSerializer(many=True, help_text="Championship order.")


class SeasonMatrixView(PublicDetailView):
    @extend_schema(
        tags=["seasons"], summary="Drivers x rounds results grid", responses=MatrixSerializer
    )
    def get(self, request, year):
        season = get_object_or_404(Season, year=year)
        return Response(MatrixSerializer(selectors.season_matrix(season)).data)

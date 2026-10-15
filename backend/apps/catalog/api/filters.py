"""Validation of query parameters. Invalid values give a 400 instead of being ignored."""

from rest_framework import serializers

from ..selectors import (
    CIRCUIT_ORDERINGS,
    CONSTRUCTOR_ORDERINGS,
    DRIVER_ORDERINGS,
    SEARCH_MIN_LENGTH,
)

MIN_YEAR = 1950
MAX_YEAR = 2100


def _ordering_choices(orderings: dict) -> list[str]:
    return [*orderings, *(f"-{name}" for name in orderings)]


class DriverFiltersSerializer(serializers.Serializer):
    season = serializers.IntegerField(
        required=False, min_value=MIN_YEAR, max_value=MAX_YEAR, help_text="Started in this year."
    )
    nationality = serializers.CharField(required=False, max_length=100)
    constructor = serializers.SlugField(required=False, help_text="Constructor slug.")
    champion = serializers.BooleanField(
        required=False,
        allow_null=True,
        help_text="true: only world champions; false: only drivers without a title.",
    )
    active = serializers.BooleanField(
        required=False, allow_null=True, help_text="Raced in the latest season with results."
    )
    q = serializers.CharField(
        required=False, max_length=100, help_text="Case and diacritics insensitive name search."
    )
    ordering = serializers.ChoiceField(
        required=False, choices=_ordering_choices(DRIVER_ORDERINGS), default="family_name"
    )


class ConstructorFiltersSerializer(serializers.Serializer):
    season = serializers.IntegerField(required=False, min_value=MIN_YEAR, max_value=MAX_YEAR)
    nationality = serializers.CharField(required=False, max_length=100)
    q = serializers.CharField(required=False, max_length=100)
    ordering = serializers.ChoiceField(
        required=False, choices=_ordering_choices(CONSTRUCTOR_ORDERINGS), default="name"
    )


class CircuitFiltersSerializer(serializers.Serializer):
    country = serializers.CharField(required=False, max_length=100)
    q = serializers.CharField(required=False, max_length=100)
    ordering = serializers.ChoiceField(
        required=False, choices=_ordering_choices(CIRCUIT_ORDERINGS), default="name"
    )


class ResultsQuerySerializer(serializers.Serializer):
    session = serializers.ChoiceField(
        required=False,
        choices=["RACE", "SPRINT", "Q"],
        default="RACE",
        help_text="RACE (default), SPRINT or Q (qualifying).",
    )


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=SEARCH_MIN_LENGTH, max_length=100)

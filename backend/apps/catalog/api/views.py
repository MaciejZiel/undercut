"""Thin read-only views: validate input, call a selector, serialise."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    PolymorphicProxySerializer,
    extend_schema,
)
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import selectors
from ..models import Circuit, Constructor, Driver, Round, Season, Session
from . import filters, serializers
from .pagination import CatalogPagination


def _validated(serializer_class, request) -> dict:
    serializer = serializer_class(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class PublicReadMixin:
    """Anonymous GET-only access; no session lookup, so responses are cacheable."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]


class PublicListView(PublicReadMixin, ListAPIView):
    pagination_class = CatalogPagination


class PublicDetailView(PublicReadMixin, APIView):
    pass


# --- Drivers ---------------------------------------------------------------------------------


@extend_schema(
    tags=["drivers"],
    summary="List drivers",
    parameters=[filters.DriverFiltersSerializer],
)
class DriverListView(PublicListView):
    serializer_class = serializers.DriverListSerializer

    def get_queryset(self):
        data = _validated(filters.DriverFiltersSerializer, self.request)
        return selectors.driver_list(
            season=data.get("season"),
            nationality=data.get("nationality"),
            constructor=data.get("constructor"),
            active=data.get("active"),
            champion=data.get("champion"),
            q=data.get("q"),
            ordering=data["ordering"],
        )


class DriverDetailView(PublicDetailView):
    @extend_schema(
        tags=["drivers"], summary="Driver career", responses=serializers.DriverDetailSerializer
    )
    def get(self, request, slug):
        driver = selectors.driver_list(with_titles=False).filter(slug=slug).first()
        if driver is None:
            get_object_or_404(Driver, slug=slug)  # raises the 404
        summary = selectors.driver_title_summary(driver)
        data = {
            "slug": driver.slug,
            "given_name": driver.given_name,
            "family_name": driver.family_name,
            "code": driver.code or None,
            "number": driver.permanent_number,
            "nationality": driver.nationality or None,
            "date_of_birth": driver.dob,
            "team": selectors.team_ref(
                driver.last_constructor_slug,
                driver.last_constructor_name,
                driver.last_constructor_color,
            ),
            "stats": selectors.driver_career_stats(driver, summary),
            "seasons": selectors.driver_seasons(driver, summary),
            "last_results": selectors.driver_last_results(driver),
        }
        return Response(serializers.DriverDetailSerializer(data).data)


# --- Constructors ----------------------------------------------------------------------------


@extend_schema(
    tags=["constructors"],
    summary="List constructors",
    parameters=[filters.ConstructorFiltersSerializer],
)
class ConstructorListView(PublicListView):
    serializer_class = serializers.ConstructorListSerializer

    def get_queryset(self):
        data = _validated(filters.ConstructorFiltersSerializer, self.request)
        return selectors.constructor_list(
            season=data.get("season"),
            nationality=data.get("nationality"),
            q=data.get("q"),
            ordering=data["ordering"],
        )


class ConstructorDetailView(PublicDetailView):
    @extend_schema(
        tags=["constructors"],
        summary="Constructor history",
        responses=serializers.ConstructorDetailSerializer,
    )
    def get(self, request, slug):
        constructor = get_object_or_404(Constructor, slug=slug)
        summary = selectors.constructor_title_summary(constructor)
        seasons, current_drivers, latest = selectors.constructor_seasons(constructor, summary)
        data = {
            "slug": constructor.slug,
            "name": constructor.name,
            "nationality": constructor.nationality or None,
            "stats": selectors.constructor_career_stats(constructor, summary),
            "seasons": seasons,
            "current_season": latest,
            "current_drivers": current_drivers,
        }
        return Response(serializers.ConstructorDetailSerializer(data).data)


# --- Circuits --------------------------------------------------------------------------------


@extend_schema(
    tags=["circuits"],
    summary="List circuits",
    parameters=[filters.CircuitFiltersSerializer],
)
class CircuitListView(PublicListView):
    serializer_class = serializers.CircuitListSerializer

    def get_queryset(self):
        data = _validated(filters.CircuitFiltersSerializer, self.request)
        return selectors.circuit_list(
            country=data.get("country"), q=data.get("q"), ordering=data["ordering"]
        )


class CircuitDetailView(PublicDetailView):
    @extend_schema(
        tags=["circuits"], summary="Circuit page", responses=serializers.CircuitDetailSerializer
    )
    def get(self, request, slug):
        circuit = selectors.circuit_with_counts(slug)
        if circuit is None:
            get_object_or_404(Circuit, slug=slug)  # raises the 404
        winners = selectors.circuit_winners(circuit)
        record = selectors.circuit_lap_record(circuit)
        length_m, length_is_estimate = selectors.circuit_length(circuit)
        data = {
            "slug": circuit.slug,
            "name": circuit.name,
            "locality": circuit.locality or None,
            "country": circuit.country or None,
            "lat": None if circuit.lat is None else float(circuit.lat),
            "lng": None if circuit.lng is None else float(circuit.lng),
            "timezone": circuit.timezone or None,
            "length_m": length_m,
            "length_is_estimate": length_is_estimate,
            "lap_record_ms": record["time_ms"] if record else None,
            "lap_record_driver": record["driver"] if record else None,
            "lap_record_year": record["year"] if record else None,
            "outline": selectors.circuit_outline(circuit),
            "gp_count": circuit.gp_count,
            "last_gp_date": circuit.last_gp_date,
            "winners": winners,
            "most_wins_drivers": selectors.most_wins(winners, "driver"),
            "most_wins_teams": selectors.most_wins(winners, "team"),
        }
        return Response(serializers.CircuitDetailSerializer(data).data)


# --- Seasons and rounds ----------------------------------------------------------------------


@extend_schema(tags=["seasons"], summary="List seasons")
class SeasonListView(PublicListView):
    serializer_class = serializers.SeasonListSerializer

    def get_queryset(self):
        return selectors.season_list()

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        if page:
            champions = selectors.season_champions(season.year for season in page)
            for season in page:
                for key, value in champions.get(season.year, {}).items():
                    setattr(season, key, value)
        return page


class SeasonDetailView(PublicDetailView):
    @extend_schema(
        tags=["seasons"],
        summary="Season calendar",
        responses=serializers.SeasonDetailSerializer,
    )
    def get(self, request, year):
        season = get_object_or_404(Season, year=year)
        calendar = selectors.season_calendar(season)
        data = {
            "year": season.year,
            "name": season.name or None,
            "sprint_rounds": sum(1 for r in calendar if r["has_sprint"]),
            "rounds": calendar,
        }
        return Response(serializers.SeasonDetailSerializer(data).data)


def _get_round(year: int, number: int) -> Round:
    return get_object_or_404(
        Round.objects.select_related("season", "circuit"), season__year=year, round=number
    )


class RoundDetailView(PublicDetailView):
    @extend_schema(
        tags=["rounds"], summary="Race weekend header", responses=serializers.RoundDetailSerializer
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        round_ = _get_round(year, round)
        return Response(serializers.RoundDetailSerializer(selectors.round_detail(round_)).data)


class RoundResultsView(PublicDetailView):
    @extend_schema(
        tags=["rounds"],
        summary="Session results",
        parameters=[filters.ResultsQuerySerializer],
        responses=PolymorphicProxySerializer(
            component_name="SessionResults",
            serializers=[
                serializers.RaceSessionResultsSerializer,
                serializers.QualifyingSessionResultsSerializer,
            ],
            resource_type_field_name=None,
        ),
    )
    def get(self, request, year, round):  # noqa: A002 - URL keyword
        data = _validated(filters.ResultsQuerySerializer, request)
        round_ = _get_round(year, round)
        session = get_object_or_404(Session, round=round_, type=data["session"])
        body = {
            "year": round_.season.year,
            "round": round_.round,
            "session": {"type": session.type, "status": session.status},
            "results": selectors.session_results(round_, session),
        }
        serializer_class = (
            serializers.QualifyingSessionResultsSerializer
            if session.type == Session.Type.Q
            else serializers.RaceSessionResultsSerializer
        )
        return Response(serializer_class(body).data)


# --- Search ----------------------------------------------------------------------------------


class SearchView(PublicDetailView):
    @extend_schema(
        tags=["search"],
        summary="Global search",
        parameters=[
            OpenApiParameter(
                "q",
                str,
                required=True,
                description="At least 2 characters; case and diacritics insensitive.",
            )
        ],
        responses=serializers.SearchSerializer,
    )
    def get(self, request):
        data = _validated(filters.SearchQuerySerializer, request)
        return Response(serializers.SearchSerializer(selectors.search(data["q"])).data)

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import errors, selectors, services
from . import serializers as s

# Everything not listed is a plain 400.
HTTP_STATUS = {
    errors.RoundNotFound: 404,
    errors.LeagueNotFound: 404,
    errors.PredictionsLocked: 403,
    errors.PicksHidden: 403,
    errors.EmailNotVerified: 403,
    errors.NotLeagueMember: 404,  # do not reveal that a league exists
    errors.NotLeagueOwner: 403,
    errors.OwnerCannotLeave: 409,
    errors.QualifyingTimeUnknown: 409,
    errors.RoundCancelled: 409,
    errors.AlreadyMember: 409,
    errors.LeagueFull: 409,
    errors.LeagueLimitReached: 409,
}


class DomainErrorMixin:
    """Turn domain errors into {"detail", "code"} responses with the right status."""

    def handle_exception(self, exc):
        if isinstance(exc, errors.PredictionsError):
            http_status = HTTP_STATUS.get(type(exc), 400)
            return Response({"detail": str(exc), "code": exc.code}, status=http_status)
        return super().handle_exception(exc)


class BaseView(DomainErrorMixin, APIView):
    pass


ERRORS = {
    400: s.PredictionErrorSerializer,
    403: s.PredictionErrorSerializer,
    404: s.PredictionErrorSerializer,
}


class RoundPredictionView(BaseView):
    """Read the state of a round (public) and submit or change my pick (auth)."""

    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticated()]
        return super().get_permissions()

    @extend_schema(
        responses={200: s.RoundStateSerializer, 404: s.PredictionErrorSerializer},
        summary="Prediction state of a round: open or closed, closing time, my pick",
    )
    def get(self, request, year, round):
        round_ = services.resolve_round(year, round)
        return Response(selectors.round_state(request.user, round_))

    @extend_schema(
        request=s.PickInputSerializer,
        responses={
            200: s.RoundStateSerializer,
            201: s.RoundStateSerializer,
            **ERRORS,
            409: s.PredictionErrorSerializer,
        },
        summary="Submit or change my pick; 403 after predictions close",
    )
    def put(self, request, year, round):
        data = s.PickInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        _, created = services.submit_prediction(
            request.user, year, round, services.PickInput(**data.validated_data)
        )
        round_ = services.resolve_round(year, round)
        return Response(
            selectors.round_state(request.user, round_),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RoundStatsView(BaseView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: s.PickStatsSerializer,
            403: s.PredictionErrorSerializer,
            404: s.PredictionErrorSerializer,
        },
        summary="Global pick statistics of a round (after predictions close)",
    )
    def get(self, request, year, round):
        return Response(selectors.pick_stats(services.resolve_round(year, round)))


class HistoryView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=s.HistoryRowSerializer(many=True), summary="My prediction history")
    def get(self, request):
        return Response(selectors.history(request.user))


class LeaderboardView(BaseView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[s.LeaderboardQuerySerializer],
        responses={200: s.LeaderboardSerializer, 404: s.PredictionErrorSerializer},
        summary="Leaderboard (global, per round or league)",
    )
    def get(self, request):
        params = s.LeaderboardQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        league = None
        if "league" in data:
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentication required.", "code": "not_authenticated"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            league = services.get_league(data["league"])
            services.require_member(request.user, league)
        return Response(
            selectors.leaderboard(
                season=data.get("season"),
                round_number=data.get("round"),
                league=league,
                limit=data["limit"],
                offset=data["offset"],
            )
        )


class LeagueListCreateView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=s.LeagueSummarySerializer(many=True), summary="My leagues")
    def get(self, request):
        return Response(selectors.my_leagues(request.user))

    @extend_schema(
        request=s.LeagueCreateSerializer,
        responses={
            201: s.LeagueDetailSerializer,
            400: s.PredictionErrorSerializer,
            409: s.PredictionErrorSerializer,
        },
        summary="Create a league (max 10 per user)",
    )
    def post(self, request):
        data = s.LeagueCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        league = services.create_league(request.user, data.validated_data["name"])
        return Response(
            selectors.league_detail(league, request.user), status=status.HTTP_201_CREATED
        )


class LeagueJoinView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=s.LeagueJoinSerializer,
        responses={
            200: s.LeagueDetailSerializer,
            404: s.PredictionErrorSerializer,
            409: s.PredictionErrorSerializer,
        },
        summary="Join a league by invite code (max 50 members)",
    )
    def post(self, request):
        data = s.LeagueJoinSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        league = services.join_league(request.user, data.validated_data["code"])
        return Response(selectors.league_detail(league, request.user))


class LeagueDetailView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: s.LeagueDetailSerializer, 404: s.PredictionErrorSerializer},
        summary="League details (members only)",
    )
    def get(self, request, code):
        league = services.get_league(code)
        services.require_member(request.user, league)
        return Response(selectors.league_detail(league, request.user))

    @extend_schema(
        responses={204: None, 403: s.PredictionErrorSerializer, 404: s.PredictionErrorSerializer},
        summary="Delete a league (owner)",
    )
    def delete(self, request, code):
        services.delete_league(request.user, code)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeagueMemberView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={204: None, 403: s.PredictionErrorSerializer, 404: s.PredictionErrorSerializer},
        summary="Remove a member (owner)",
    )
    def delete(self, request, code, user_id):
        services.remove_member(request.user, code, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeagueLeaveView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: None, 404: s.PredictionErrorSerializer, 409: s.PredictionErrorSerializer},
        summary="Leave a league",
    )
    def post(self, request, code):
        services.leave_league(request.user, code)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeagueRenewCodeView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: s.LeagueDetailSerializer,
            403: s.PredictionErrorSerializer,
            404: s.PredictionErrorSerializer,
        },
        summary="Renew the invite code (owner); the old code stops working",
    )
    def post(self, request, code):
        league = services.renew_code(request.user, code)
        return Response(selectors.league_detail(league, request.user))


class LeaguePicksView(BaseView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: s.MemberPickSerializer(many=True),
            403: s.PredictionErrorSerializer,
            404: s.PredictionErrorSerializer,
        },
        summary="All members' picks for a round (after predictions close)",
        parameters=[OpenApiParameter("code", str, OpenApiParameter.PATH)],
    )
    def get(self, request, code, year, round):
        league = services.get_league(code)
        services.require_member(request.user, league)
        return Response(selectors.league_picks(league, services.resolve_round(year, round)))

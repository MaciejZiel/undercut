from django.urls import path

from . import views

urlpatterns = [
    path(
        "predictions/rounds/<int:year>/<int:round>/",
        views.RoundPredictionView.as_view(),
        name="predictions-round",
    ),
    path(
        "predictions/rounds/<int:year>/<int:round>/stats/",
        views.RoundStatsView.as_view(),
        name="predictions-round-stats",
    ),
    path("predictions/history/", views.HistoryView.as_view(), name="predictions-history"),
    path(
        "predictions/leaderboard/", views.LeaderboardView.as_view(), name="predictions-leaderboard"
    ),
    path("leagues/", views.LeagueListCreateView.as_view(), name="leagues"),
    path("leagues/join/", views.LeagueJoinView.as_view(), name="leagues-join"),
    path("leagues/<str:code>/", views.LeagueDetailView.as_view(), name="league-detail"),
    path(
        "leagues/<str:code>/members/<int:user_id>/",
        views.LeagueMemberView.as_view(),
        name="league-member",
    ),
    path("leagues/<str:code>/leave/", views.LeagueLeaveView.as_view(), name="league-leave"),
    path(
        "leagues/<str:code>/renew-code/",
        views.LeagueRenewCodeView.as_view(),
        name="league-renew-code",
    ),
    path(
        "leagues/<str:code>/rounds/<int:year>/<int:round>/picks/",
        views.LeaguePicksView.as_view(),
        name="league-picks",
    ),
]

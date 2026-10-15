from django.urls import path

from . import views

urlpatterns = [
    path("standings/drivers/", views.DriverStandingsView.as_view(), name="standings-drivers"),
    path(
        "standings/drivers/progress/",
        views.DriverProgressView.as_view(),
        name="standings-drivers-progress",
    ),
    path(
        "standings/constructors/",
        views.ConstructorStandingsView.as_view(),
        name="standings-constructors",
    ),
    path(
        "standings/constructors/progress/",
        views.ConstructorProgressView.as_view(),
        name="standings-constructors-progress",
    ),
]

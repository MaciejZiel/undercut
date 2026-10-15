from django.urls import path

from . import calendar, compare, dashboard, matrix, views

urlpatterns = [
    path("drivers/", views.DriverListView.as_view(), name="driver-list"),
    path("drivers/<slug:slug>/", views.DriverDetailView.as_view(), name="driver-detail"),
    path("constructors/", views.ConstructorListView.as_view(), name="constructor-list"),
    path(
        "constructors/<slug:slug>/",
        views.ConstructorDetailView.as_view(),
        name="constructor-detail",
    ),
    path("circuits/", views.CircuitListView.as_view(), name="circuit-list"),
    path("circuits/<slug:slug>/", views.CircuitDetailView.as_view(), name="circuit-detail"),
    path("seasons/", views.SeasonListView.as_view(), name="season-list"),
    path("seasons/<int:year>/", views.SeasonDetailView.as_view(), name="season-detail"),
    path("rounds/<int:year>/<int:round>/", views.RoundDetailView.as_view(), name="round-detail"),
    path(
        "rounds/<int:year>/<int:round>/results/",
        views.RoundResultsView.as_view(),
        name="round-results",
    ),
    path("search/", views.SearchView.as_view(), name="search"),
    path("calendar/", calendar.CalendarView.as_view(), name="calendar"),
    path("calendar/ics/", calendar.CalendarIcsView.as_view(), name="calendar-ics"),
    path("dashboard/", dashboard.DashboardView.as_view(), name="dashboard"),
    path("compare/", compare.CompareView.as_view(), name="compare"),
    path("seasons/<int:year>/matrix/", matrix.SeasonMatrixView.as_view(), name="season-matrix"),
]

from django.urls import path

from . import views

BASE = "rounds/<int:year>/<int:round>/analytics"

urlpatterns = [
    path(f"{BASE}/positions/", views.PositionsView.as_view(), name="analytics-positions"),
    path(f"{BASE}/laps/", views.LapsView.as_view(), name="analytics-laps"),
    path(f"{BASE}/stints/", views.StintsView.as_view(), name="analytics-stints"),
    path(f"{BASE}/pit-stops/", views.PitStopsView.as_view(), name="analytics-pit-stops"),
    path(f"{BASE}/weather/", views.WeatherView.as_view(), name="analytics-weather"),
    path(f"{BASE}/race-control/", views.RaceControlView.as_view(), name="analytics-race-control"),
]

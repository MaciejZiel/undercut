from django.urls import path

from . import views

urlpatterns = [
    path(
        "notifications/unsubscribe/<str:token>/",
        views.UnsubscribeView.as_view(),
        name="notifications-unsubscribe",
    ),
]

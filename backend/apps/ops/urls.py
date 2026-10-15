from django.urls import path

from . import views

# Mounted at the project root (see config/urls.py): /api/ready/ and /api/v1/ops/status/.
urlpatterns = [
    path("api/ready/", views.ready, name="ready"),
    path("api/v1/ops/status/", views.OpsStatusView.as_view(), name="ops-status"),
]

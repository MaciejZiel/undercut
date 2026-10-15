from django.urls import include, path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/demo/", views.DemoLoginView.as_view(), name="auth-demo"),
    # Registration, e-mail confirmation, login/logout, password reset and change, e-mail management:
    # django-allauth headless (browser client, session based), e.g.
    #   POST /api/v1/allauth/browser/v1/auth/signup | login | email/verify | password/request ...
    #   DELETE /api/v1/allauth/browser/v1/auth/session (logout)
    path("allauth/", include("allauth.headless.urls")),
    path("account/settings/", views.SettingsView.as_view(), name="account-settings"),
    path("account/export/", views.ExportView.as_view(), name="account-export"),
    path("account/delete/", views.DeleteAccountView.as_view(), name="account-delete"),
    path("favorites/", views.FavoritesView.as_view(), name="favorites"),
    path(
        "favorites/drivers/<slug:slug>/",
        views.FavoriteDriverView.as_view(),
        name="favorite-driver",
    ),
    path(
        "favorites/constructors/<slug:slug>/",
        views.FavoriteConstructorView.as_view(),
        name="favorite-constructor",
    ),
]

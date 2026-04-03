"""accounts/urls.py"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    UserDetailView,
    UserListView,
)

urlpatterns = [
    # ── Public ──────────────────────────────────────────────────
    path("register/",        RegisterView.as_view(),    name="auth-register"),
    path("login/",           LoginView.as_view(),        name="auth-login"),
    path("token/refresh/",   TokenRefreshView.as_view(), name="token-refresh"),

    # ── Authenticated ────────────────────────────────────────────
    path("logout/",          LogoutView.as_view(),       name="auth-logout"),
    path("me/",              MeView.as_view(),            name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(),name="auth-change-password"),

    # ── Admin only ───────────────────────────────────────────────
    path("users/",           UserListView.as_view(),     name="user-list"),
    path("users/<uuid:pk>/", UserDetailView.as_view(),   name="user-detail"),
]

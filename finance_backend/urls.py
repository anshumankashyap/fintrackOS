"""
finance_backend/urls.py
────────────────────────
Root URL configuration — wires all app routes under /api/v1/
and mounts Swagger UI + ReDoc at /api/docs/.
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # Web UI (Django templates + static JS)
    path("", RedirectView.as_view(pattern_name="web-dashboard-overview", permanent=False)),
    path("accounts/", include("accounts.web_urls")),
    path("dashboard/", include("dashboard.web_urls")),
    path("records/", include("records.web_urls")),

    # API v1
    path("api/v1/auth/",      include("accounts.urls")),
    path("api/v1/records/",   include("records.urls")),
    path("api/v1/dashboard/", include("dashboard.urls")),

    # OpenAPI Schema & Docs
    path("api/schema/",       SpectacularAPIView.as_view(),       name="schema"),
    path("api/docs/",         SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",        SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
]

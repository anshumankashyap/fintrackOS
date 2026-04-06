from django.urls import path

from .web_views import DashboardOverviewView, DashboardReportsView

urlpatterns = [
    path("", DashboardOverviewView.as_view(), name="web-dashboard-overview"),
    path("reports/", DashboardReportsView.as_view(), name="web-dashboard-reports"),
]

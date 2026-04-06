"""dashboard/urls.py"""
from django.urls import path

from .views import MonthlyReportView, RecentActivityView, SummaryView, WeeklyReportView

urlpatterns = [
    path("summary/", SummaryView.as_view(), name="dashboard-summary"),
    path("monthly-report/", MonthlyReportView.as_view(), name="dashboard-monthly"),
    path("weekly-report/", WeeklyReportView.as_view(), name="dashboard-weekly"),
    path("recent-activity/", RecentActivityView.as_view(), name="dashboard-recent"),
]

"""dashboard/urls.py"""
from django.urls import path
from .views import MonthlyReportView, SummaryView

urlpatterns = [
    path("summary/",        SummaryView.as_view(),       name="dashboard-summary"),
    path("monthly-report/", MonthlyReportView.as_view(), name="dashboard-monthly"),
]

"""records/urls.py"""
from django.urls import path
from .views import FinancialRecordDetailView, FinancialRecordListCreateView

urlpatterns = [
    path("",          FinancialRecordListCreateView.as_view(), name="record-list-create"),
    path("<uuid:pk>/", FinancialRecordDetailView.as_view(),     name="record-detail"),
]

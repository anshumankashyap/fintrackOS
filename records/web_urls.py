from django.urls import path

from .web_views import TransactionsPageView

urlpatterns = [
    path("transactions/", TransactionsPageView.as_view(), name="web-records-transactions"),
]

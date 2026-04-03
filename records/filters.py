"""
records/filters.py
───────────────────
FilterSet for FinancialRecord.

Supported query parameters:
  ?category=Rent
  ?transaction_type=expense
  ?date_from=2024-01-01
  ?date_to=2024-12-31
  ?amount_min=100
  ?amount_max=5000
  ?search=salary          (title / description / category full-text search)
  ?ordering=-date         (any declared ordering field)
"""

import django_filters
from django.db.models import Q

from .models import FinancialRecord, TransactionType


class FinancialRecordFilter(django_filters.FilterSet):

    # Exact matches
    category         = django_filters.CharFilter(lookup_expr="iexact")
    transaction_type = django_filters.ChoiceFilter(choices=TransactionType.choices)

    # Date range
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to   = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    # Amount range
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    # Full-text search across title + description + category
    search = django_filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(category__icontains=value)
        )

    class Meta:
        model  = FinancialRecord
        fields = [
            "category", "transaction_type",
            "date_from", "date_to",
            "amount_min", "amount_max",
            "search",
        ]

"""
dashboard/services.py
──────────────────────
Pure business logic — no Django views, no HTTP concerns.
All financial calculations live here so they can be:
  - tested independently
  - reused across views
  - cached efficiently

Public API:
  DashboardService.get_summary(queryset)        → SummaryResult
  DashboardService.get_monthly_report(queryset) → list[MonthlyReportEntry]
  DashboardService.get_category_breakdown(qs)   → list[CategoryBreakdown]
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from django.db.models import DecimalField, Q, QuerySet, Sum
from django.db.models.functions import TruncMonth

logger = logging.getLogger("finance")

ZERO = Decimal("0.00")


# ── Data Transfer Objects ─────────────────────────────────────────

@dataclass
class CategoryBreakdown:
    category: str
    total_income:  Decimal
    total_expense: Decimal
    net:           Decimal
    record_count:  int


@dataclass
class MonthlyReportEntry:
    year:          int
    month:         int
    month_name:    str
    total_income:  Decimal
    total_expense: Decimal
    net_balance:   Decimal
    record_count:  int


@dataclass
class SummaryResult:
    total_income:       Decimal
    total_expense:      Decimal
    net_balance:        Decimal
    total_records:      int
    income_records:     int
    expense_records:    int
    category_breakdown: List[CategoryBreakdown] = field(default_factory=list)

    @property
    def is_profitable(self) -> bool:
        return self.net_balance >= ZERO


# ── Month name helper ─────────────────────────────────────────────

_MONTHS = [
    "", "January", "February", "March", "April",
    "May", "June", "July", "August", "September",
    "October", "November", "December",
]


# ── Service Class ─────────────────────────────────────────────────

class DashboardService:
    """
    Stateless service — all methods are class-level and accept a
    queryset so callers can pre-filter by date range, user, etc.
    """

    @classmethod
    def get_summary(cls, queryset: QuerySet) -> SummaryResult:
        """
        Calculate total income, total expenses, net balance, and
        a per-category breakdown from the given queryset.

        Uses a single DB query for the top-level aggregates, then
        a second query for the category breakdown.
        """
        from records.models import TransactionType

        # ── Aggregate totals in a single DB round-trip ─────────────
        aggregates = queryset.aggregate(
            total_income=Sum(
                "amount",
                filter=Q(transaction_type=TransactionType.INCOME),
                output_field=DecimalField(),
            ),
            total_expense=Sum(
                "amount",
                filter=Q(transaction_type=TransactionType.EXPENSE),
                output_field=DecimalField(),
            ),
            income_count=Sum(
                "id",
                filter=Q(transaction_type=TransactionType.INCOME),
                output_field=DecimalField(),
            ),
        )

        total_income  = aggregates["total_income"]  or ZERO
        total_expense = aggregates["total_expense"] or ZERO
        net_balance   = total_income - total_expense

        total_records   = queryset.count()
        income_records  = queryset.filter(transaction_type=TransactionType.INCOME).count()
        expense_records = queryset.filter(transaction_type=TransactionType.EXPENSE).count()

        # ── Category breakdown ────────────────────────────────────
        category_breakdown = cls.get_category_breakdown(queryset)

        return SummaryResult(
            total_income       = total_income,
            total_expense      = total_expense,
            net_balance        = net_balance,
            total_records      = total_records,
            income_records     = income_records,
            expense_records    = expense_records,
            category_breakdown = category_breakdown,
        )

    @classmethod
    def get_category_breakdown(cls, queryset: QuerySet) -> List[CategoryBreakdown]:
        """
        Return income, expense, and net per category, sorted by
        total absolute value descending.
        """
        from records.models import TransactionType

        categories = (
            queryset.values("category")
            .annotate(
                total_income=Sum(
                    "amount",
                    filter=Q(transaction_type=TransactionType.INCOME),
                    output_field=DecimalField(),
                ),
                total_expense=Sum(
                    "amount",
                    filter=Q(transaction_type=TransactionType.EXPENSE),
                    output_field=DecimalField(),
                ),
            )
            .order_by("category")
        )

        result = []
        for row in categories:
            inc = row["total_income"]  or ZERO
            exp = row["total_expense"] or ZERO
            result.append(
                CategoryBreakdown(
                    category      = row["category"],
                    total_income  = inc,
                    total_expense = exp,
                    net           = inc - exp,
                    record_count  = queryset.filter(category=row["category"]).count(),
                )
            )

        # Sort: largest absolute total first
        result.sort(key=lambda x: abs(x.total_income + x.total_expense), reverse=True)
        return result

    @classmethod
    def get_monthly_report(
        cls,
        queryset: QuerySet,
        limit: int = 12,
    ) -> List[MonthlyReportEntry]:
        """
        Return monthly income/expense/net trends, newest month first.
        Default: last 12 months of data present in the queryset.

        Uses TruncMonth for DB-side grouping — no Python loops over records.
        """
        from records.models import TransactionType

        monthly_data = (
            queryset.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(
                total_income=Sum(
                    "amount",
                    filter=Q(transaction_type=TransactionType.INCOME),
                    output_field=DecimalField(),
                ),
                total_expense=Sum(
                    "amount",
                    filter=Q(transaction_type=TransactionType.EXPENSE),
                    output_field=DecimalField(),
                ),
            )
            .order_by("-month")[:limit]
        )

        result = []
        for row in monthly_data:
            month_dt = row["month"]
            inc = row["total_income"]  or ZERO
            exp = row["total_expense"] or ZERO
            result.append(
                MonthlyReportEntry(
                    year          = month_dt.year,
                    month         = month_dt.month,
                    month_name    = _MONTHS[month_dt.month],
                    total_income  = inc,
                    total_expense = exp,
                    net_balance   = inc - exp,
                    record_count  = queryset.filter(
                        date__year=month_dt.year,
                        date__month=month_dt.month,
                    ).count(),
                )
            )

        return result

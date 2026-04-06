"""
dashboard/services.py
──────────────────────
Pure business logic for dashboard analytics.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import List

from django.db.models import Count, DecimalField, Q, QuerySet, Sum
from django.db.models.functions import TruncMonth, TruncWeek

logger = logging.getLogger("finance")

ZERO = Decimal("0.00")


@dataclass
class CategoryBreakdown:
    category: str
    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    record_count: int


@dataclass
class MonthlyReportEntry:
    year: int
    month: int
    month_name: str
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    record_count: int


@dataclass
class WeeklyReportEntry:
    week_start: date
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    record_count: int


@dataclass
class RecentActivityRow:
    title: str
    amount: Decimal
    category: str
    date: date
    transaction_type: str


@dataclass
class SummaryResult:
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    total_records: int
    income_records: int
    expense_records: int
    category_breakdown: List[CategoryBreakdown] = field(default_factory=list)

    @property
    def is_profitable(self) -> bool:
        return self.net_balance >= ZERO


_MONTHS = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


class DashboardService:
    """Stateless aggregation helpers — callers pass a pre-scoped queryset."""

    @classmethod
    def get_summary(cls, queryset: QuerySet) -> SummaryResult:
        from records.models import TransactionType

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
        )

        total_income = aggregates["total_income"] or ZERO
        total_expense = aggregates["total_expense"] or ZERO
        net_balance = total_income - total_expense

        total_records = queryset.count()
        income_records = queryset.filter(transaction_type=TransactionType.INCOME).count()
        expense_records = queryset.filter(transaction_type=TransactionType.EXPENSE).count()

        category_breakdown = cls.get_category_breakdown(queryset)

        return SummaryResult(
            total_income=total_income,
            total_expense=total_expense,
            net_balance=net_balance,
            total_records=total_records,
            income_records=income_records,
            expense_records=expense_records,
            category_breakdown=category_breakdown,
        )

    @classmethod
    def get_category_breakdown(cls, queryset: QuerySet) -> List[CategoryBreakdown]:
        from records.models import TransactionType

        rows = (
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
                record_count=Count("id"),
            )
            .order_by("category")
        )

        result = []
        for row in rows:
            inc = row["total_income"] or ZERO
            exp = row["total_expense"] or ZERO
            result.append(
                CategoryBreakdown(
                    category=row["category"],
                    total_income=inc,
                    total_expense=exp,
                    net=inc - exp,
                    record_count=row["record_count"],
                )
            )

        result.sort(key=lambda x: abs(x.total_income + x.total_expense), reverse=True)
        return result

    @classmethod
    def get_monthly_report(cls, queryset: QuerySet, limit: int = 12) -> List[MonthlyReportEntry]:
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
            inc = row["total_income"] or ZERO
            exp = row["total_expense"] or ZERO
            result.append(
                MonthlyReportEntry(
                    year=month_dt.year,
                    month=month_dt.month,
                    month_name=_MONTHS[month_dt.month],
                    total_income=inc,
                    total_expense=exp,
                    net_balance=inc - exp,
                    record_count=queryset.filter(
                        date__year=month_dt.year,
                        date__month=month_dt.month,
                    ).count(),
                )
            )

        return result

    @classmethod
    def get_weekly_report(cls, queryset: QuerySet, limit: int = 12) -> List[WeeklyReportEntry]:
        from records.models import TransactionType

        weekly_data = (
            queryset.annotate(week=TruncWeek("date"))
            .values("week")
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
            .order_by("-week")[:limit]
        )

        result = []
        for row in weekly_data:
            week_dt = row["week"]
            if hasattr(week_dt, "date"):
                week_start = week_dt.date()
            else:
                week_start = week_dt
            inc = row["total_income"] or ZERO
            exp = row["total_expense"] or ZERO
            result.append(
                WeeklyReportEntry(
                    week_start=week_start,
                    total_income=inc,
                    total_expense=exp,
                    net_balance=inc - exp,
                    record_count=queryset.filter(
                        date__gte=week_start,
                        date__lt=week_start + timedelta(days=7),
                    ).count(),
                )
            )

        return result

    @classmethod
    def get_recent_activity(cls, queryset: QuerySet, limit: int = 20) -> List[RecentActivityRow]:
        rows = queryset.order_by("-date", "-created_at")[:limit]
        return [
            RecentActivityRow(
                title=r.title,
                amount=r.amount,
                category=r.category,
                date=r.date,
                transaction_type=r.transaction_type,
            )
            for r in rows
        ]

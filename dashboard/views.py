"""
dashboard/views.py
───────────────────
Financial analytics endpoints.

  GET /api/v1/dashboard/summary/        — totals + category breakdown
  GET /api/v1/dashboard/monthly-report/ — monthly trend data

Both endpoints:
  - Require authentication (any role)
  - Support optional date-range query params: ?date_from= &date_to=
  - Are Redis-cached per (user, params) to avoid re-computing on every hit
  - Return decimal values (not floats) for precision
"""

import hashlib
import json
import logging
from datetime import datetime

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import success_response
from permissions.rbac import IsViewerOrAbove
from records.models import FinancialRecord

from .serializers import MonthlyReportSerializer, SummarySerializer
from .services import DashboardService

logger = logging.getLogger("finance")

_DATE_PARAMS = [
    OpenApiParameter(
        "date_from", description="Start date (YYYY-MM-DD). Defaults to 1 year ago.",
    ),
    OpenApiParameter(
        "date_to", description="End date (YYYY-MM-DD). Defaults to today.",
    ),
]


def _parse_date(value: str, param_name: str):
    """Parse date string; raise ValidationError on bad format."""
    from rest_framework.exceptions import ValidationError
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({param_name: f"Invalid date format. Use YYYY-MM-DD."})


def _build_cache_key(prefix: str, user_id, params: dict) -> str:
    """Deterministic cache key based on user + query params."""
    param_str = json.dumps(params, sort_keys=True)
    digest    = hashlib.md5(param_str.encode()).hexdigest()[:8]
    return f"finance:dashboard:{prefix}:{user_id}:{digest}"


def _get_filtered_queryset(request):
    """
    Return a FinancialRecord queryset optionally filtered by date range.
    Admins see all records; Viewers/Analysts see all records too (summary
    is aggregate — no PII exposed).
    """
    from datetime import date, timedelta
    qs = FinancialRecord.objects.all()

    date_from_str = request.query_params.get("date_from")
    date_to_str   = request.query_params.get("date_to")

    if date_from_str:
        qs = qs.filter(date__gte=_parse_date(date_from_str, "date_from"))
    if date_to_str:
        qs = qs.filter(date__lte=_parse_date(date_to_str, "date_to"))

    return qs


# ── Summary ───────────────────────────────────────────────────────

@extend_schema(tags=["Dashboard"], parameters=_DATE_PARAMS)
class SummaryView(APIView):
    """
    Returns aggregated financial summary:
      - total income and expense
      - net balance
      - income / expense record counts
      - whether the period is profitable
      - per-category income / expense breakdown

    Results are cached for 5 minutes (CACHE_TTL) per user + date range.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request):
        cache_key = _build_cache_key("summary", request.user.id, dict(request.query_params))
        cached    = cache.get(cache_key)
        if cached:
            logger.debug("Dashboard summary cache hit: %s", cache_key)
            return success_response(data=cached, message="Financial summary (cached).")

        qs      = _get_filtered_queryset(request)
        summary = DashboardService.get_summary(qs)
        data    = SummarySerializer(summary).data

        cache.set(cache_key, data)
        logger.info("Dashboard summary computed for user %s", request.user.email)
        return success_response(data=data, message="Financial summary.")


# ── Monthly Report ────────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    parameters=_DATE_PARAMS + [
        OpenApiParameter(
            "months",
            description="Number of months to include in the report (default 12, max 60).",
        )
    ],
)
class MonthlyReportView(APIView):
    """
    Returns month-by-month income/expense trends.
    Useful for plotting a time-series chart on the frontend.

    Each entry contains:
      - year, month number, month name
      - total_income, total_expense, net_balance
      - record_count for the month
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    def get(self, request):
        # Parse optional limit
        try:
            limit = int(request.query_params.get("months", 12))
            limit = max(1, min(limit, 60))   # clamp to [1, 60]
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"months": "Must be an integer between 1 and 60."})

        cache_key = _build_cache_key("monthly", request.user.id, {
            **dict(request.query_params),
            "_limit": limit,
        })
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Monthly report cache hit: %s", cache_key)
            return success_response(data=cached, message="Monthly report (cached).")

        qs      = _get_filtered_queryset(request)
        monthly = DashboardService.get_monthly_report(qs, limit=limit)
        data    = {
            "period_months":  limit,
            "monthly_trends": [
                {
                    "year":          e.year,
                    "month":         e.month,
                    "month_name":    e.month_name,
                    "total_income":  str(e.total_income),
                    "total_expense": str(e.total_expense),
                    "net_balance":   str(e.net_balance),
                    "record_count":  e.record_count,
                }
                for e in monthly
            ],
        }
        cache.set(cache_key, data)
        logger.info("Monthly report computed for user %s", request.user.email)
        return success_response(data=data, message="Monthly financial report.")

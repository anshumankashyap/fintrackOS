"""
dashboard/views.py
───────────────────
Financial analytics endpoints (scoped per user; Admin sees all).

  GET /api/v1/dashboard/summary/
  GET /api/v1/dashboard/monthly-report/
  GET /api/v1/dashboard/weekly-report/
  GET /api/v1/dashboard/recent-activity/
"""

import hashlib
import json
import logging
from datetime import datetime

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import success_response
from permissions.rbac import CanAccessDashboard
from records.models import FinancialRecord

from .serializers import SummarySerializer
from .services import DashboardService

logger = logging.getLogger("finance")

_DATE_PARAMS = [
    OpenApiParameter(
        "date_from",
        description="Start date (YYYY-MM-DD).",
    ),
    OpenApiParameter(
        "date_to",
        description="End date (YYYY-MM-DD).",
    ),
]


def _parse_date(value: str, param_name: str):
    from rest_framework.exceptions import ValidationError

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({param_name: "Invalid date format. Use YYYY-MM-DD."})


def _build_cache_key(prefix: str, user_id, params: dict) -> str:
    param_str = json.dumps(params, sort_keys=True)
    digest = hashlib.md5(param_str.encode()).hexdigest()[:8]
    return f"finance:dashboard:{prefix}:{user_id}:{digest}"


def _scoped_records(request):
    """Dashboard data scope: own records unless Admin."""
    qs = FinancialRecord.objects.select_related("created_by")
    if not request.user.is_admin:
        qs = qs.filter(created_by=request.user)
    return qs


def _get_filtered_queryset(request):
    qs = _scoped_records(request)
    date_from_str = request.query_params.get("date_from")
    date_to_str = request.query_params.get("date_to")
    if date_from_str:
        qs = qs.filter(date__gte=_parse_date(date_from_str, "date_from"))
    if date_to_str:
        qs = qs.filter(date__lte=_parse_date(date_to_str, "date_to"))
    return qs


@extend_schema(tags=["Dashboard"], parameters=_DATE_PARAMS)
class SummaryView(APIView):
    permission_classes = [IsAuthenticated, CanAccessDashboard]

    def get(self, request):
        cache_key = _build_cache_key("summary", request.user.id, dict(request.query_params))
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Dashboard summary cache hit: %s", cache_key)
            return success_response(data=cached, message="Financial summary (cached).")

        qs = _get_filtered_queryset(request)
        summary = DashboardService.get_summary(qs)
        data = SummarySerializer(summary).data
        cache.set(cache_key, data)
        logger.info("Dashboard summary computed for user %s", request.user.email)
        return success_response(data=data, message="Financial summary.")


@extend_schema(
    tags=["Dashboard"],
    parameters=_DATE_PARAMS
    + [
        OpenApiParameter(
            "months",
            description="Number of months to include (default 12, max 60).",
        )
    ],
)
class MonthlyReportView(APIView):
    permission_classes = [IsAuthenticated, CanAccessDashboard]

    def get(self, request):
        try:
            limit = int(request.query_params.get("months", 12))
            limit = max(1, min(limit, 60))
        except ValueError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"months": "Must be an integer between 1 and 60."})

        cache_key = _build_cache_key(
            "monthly",
            request.user.id,
            {**dict(request.query_params), "_limit": limit},
        )
        cached = cache.get(cache_key)
        if cached:
            return success_response(data=cached, message="Monthly report (cached).")

        qs = _get_filtered_queryset(request)
        monthly = DashboardService.get_monthly_report(qs, limit=limit)
        data = {
            "period_months": limit,
            "monthly_trends": [
                {
                    "year": e.year,
                    "month": e.month,
                    "month_name": e.month_name,
                    "total_income": str(e.total_income),
                    "total_expense": str(e.total_expense),
                    "net_balance": str(e.net_balance),
                    "record_count": e.record_count,
                }
                for e in monthly
            ],
        }
        cache.set(cache_key, data)
        logger.info("Monthly report computed for user %s", request.user.email)
        return success_response(data=data, message="Monthly financial report.")


@extend_schema(
    tags=["Dashboard"],
    parameters=_DATE_PARAMS
    + [
        OpenApiParameter(
            "weeks",
            description="Number of weeks to include (default 12, max 104).",
        )
    ],
)
class WeeklyReportView(APIView):
    permission_classes = [IsAuthenticated, CanAccessDashboard]

    def get(self, request):
        try:
            limit = int(request.query_params.get("weeks", 12))
            limit = max(1, min(limit, 104))
        except ValueError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"weeks": "Must be an integer between 1 and 104."})

        cache_key = _build_cache_key(
            "weekly",
            request.user.id,
            {**dict(request.query_params), "_limit": limit},
        )
        cached = cache.get(cache_key)
        if cached:
            return success_response(data=cached, message="Weekly report (cached).")

        qs = _get_filtered_queryset(request)
        weekly = DashboardService.get_weekly_report(qs, limit=limit)
        data = {
            "period_weeks": limit,
            "weekly_trends": [
                {
                    "week_start": str(e.week_start),
                    "total_income": str(e.total_income),
                    "total_expense": str(e.total_expense),
                    "net_balance": str(e.net_balance),
                    "record_count": e.record_count,
                }
                for e in weekly
            ],
        }
        cache.set(cache_key, data)
        return success_response(data=data, message="Weekly financial report.")


@extend_schema(
    tags=["Dashboard"],
    parameters=_DATE_PARAMS
    + [
        OpenApiParameter(
            "limit",
            description="Max rows to return (default 20, max 100).",
        )
    ],
)
class RecentActivityView(APIView):
    permission_classes = [IsAuthenticated, CanAccessDashboard]

    def get(self, request):
        try:
            lim = int(request.query_params.get("limit", 20))
            lim = max(1, min(lim, 100))
        except ValueError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"limit": "Must be an integer between 1 and 100."})

        cache_key = _build_cache_key(
            "recent",
            request.user.id,
            {**dict(request.query_params), "_limit": lim},
        )
        cached = cache.get(cache_key)
        if cached:
            return success_response(data=cached, message="Recent activity (cached).")

        qs = _get_filtered_queryset(request)
        rows = DashboardService.get_recent_activity(qs, limit=lim)
        data = {
            "limit": lim,
            "items": [
                {
                    "title": r.title,
                    "amount": str(r.amount),
                    "category": r.category,
                    "date": str(r.date),
                    "transaction_type": r.transaction_type,
                }
                for r in rows
            ],
        }
        cache.set(cache_key, data)
        return success_response(data=data, message="Recent activity.")

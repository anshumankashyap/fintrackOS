"""
dashboard/serializers.py
─────────────────────────
Read-only output serializers for dashboard responses.
These are NOT model serializers — they serialize the dataclasses
produced by DashboardService.
"""

from rest_framework import serializers


class CategoryBreakdownSerializer(serializers.Serializer):
    category      = serializers.CharField()
    total_income  = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=14, decimal_places=2)
    net           = serializers.DecimalField(max_digits=14, decimal_places=2)
    record_count  = serializers.IntegerField()


class SummarySerializer(serializers.Serializer):
    total_income        = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_expense       = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_balance         = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_records       = serializers.IntegerField()
    income_records      = serializers.IntegerField()
    expense_records     = serializers.IntegerField()
    is_profitable       = serializers.BooleanField()
    category_breakdown  = CategoryBreakdownSerializer(many=True)


class MonthlyReportEntrySerializer(serializers.Serializer):
    year          = serializers.IntegerField()
    month         = serializers.IntegerField()
    month_name    = serializers.CharField()
    total_income  = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_balance   = serializers.DecimalField(max_digits=14, decimal_places=2)
    record_count  = serializers.IntegerField()


class MonthlyReportSerializer(serializers.Serializer):
    period_months  = serializers.IntegerField()
    monthly_trends = MonthlyReportEntrySerializer(many=True)

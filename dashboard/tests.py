"""
dashboard/tests.py
───────────────────
Tests for DashboardService business logic and dashboard API endpoints.

Coverage:
  - DashboardService.get_summary (totals, net balance, category breakdown)
  - DashboardService.get_monthly_report (grouping, ordering)
  - GET /dashboard/summary/  (auth required, date filtering)
  - GET /dashboard/monthly-report/ (auth required, month limit)
  - Empty dataset edge case (all zeros)
  - Profitable vs loss period detection
"""

from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Role, User
from records.models import FinancialRecord, TransactionType

from .services import DashboardService


# Helpers

def make_user(email, role=Role.VIEWER):
    return User.objects.create_user(email=email, password="Pass1234!", role=role)

def auth_client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return c

def make_record(user, amount, t_type, category="Other", days_ago=1):
    return FinancialRecord.objects.create(
        title=f"{t_type} {amount}",
        amount=Decimal(str(amount)),
        category=category,
        transaction_type=t_type,
        date=date.today() - timedelta(days=days_ago),
        created_by=user,
    )


# Service: Summary

class DashboardServiceSummaryTest(APITestCase):

    def setUp(self):
        self.user = make_user("svc@example.com")

    def test_empty_dataset_returns_zeros(self):
        qs      = FinancialRecord.objects.none()
        summary = DashboardService.get_summary(qs)
        self.assertEqual(summary.total_income,  Decimal("0.00"))
        self.assertEqual(summary.total_expense, Decimal("0.00"))
        self.assertEqual(summary.net_balance,   Decimal("0.00"))
        self.assertEqual(summary.total_records, 0)

    def test_correct_income_total(self):
        make_record(self.user, 1000, TransactionType.INCOME)
        make_record(self.user, 500,  TransactionType.INCOME)
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        self.assertEqual(summary.total_income, Decimal("1500.00"))

    def test_correct_expense_total(self):
        make_record(self.user, 300, TransactionType.EXPENSE)
        make_record(self.user, 200, TransactionType.EXPENSE)
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        self.assertEqual(summary.total_expense, Decimal("500.00"))

    def test_net_balance_calculation(self):
        make_record(self.user, 2000, TransactionType.INCOME)
        make_record(self.user, 800,  TransactionType.EXPENSE)
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        self.assertEqual(summary.net_balance, Decimal("1200.00"))

    def test_profitable_when_income_exceeds_expenses(self):
        make_record(self.user, 5000, TransactionType.INCOME)
        make_record(self.user, 3000, TransactionType.EXPENSE)
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        self.assertTrue(summary.is_profitable)

    def test_not_profitable_when_expenses_exceed_income(self):
        make_record(self.user, 1000, TransactionType.INCOME)
        make_record(self.user, 3000, TransactionType.EXPENSE)
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        self.assertFalse(summary.is_profitable)

    def test_record_counts_split_correctly(self):
        make_record(self.user, 100, TransactionType.INCOME)
        make_record(self.user, 100, TransactionType.INCOME)
        make_record(self.user, 50,  TransactionType.EXPENSE)
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        self.assertEqual(summary.income_records,  2)
        self.assertEqual(summary.expense_records, 1)
        self.assertEqual(summary.total_records,   3)

    def test_category_breakdown_present(self):
        make_record(self.user, 1000, TransactionType.INCOME,  category="Salary")
        make_record(self.user, 400,  TransactionType.EXPENSE, category="Rent")
        qs         = FinancialRecord.objects.all()
        summary    = DashboardService.get_summary(qs)
        categories = {c.category for c in summary.category_breakdown}
        self.assertIn("Salary", categories)
        self.assertIn("Rent",   categories)

    def test_category_breakdown_net_per_category(self):
        make_record(self.user, 2000, TransactionType.INCOME,  category="Consulting")
        make_record(self.user, 500,  TransactionType.EXPENSE, category="Consulting")
        qs      = FinancialRecord.objects.all()
        summary = DashboardService.get_summary(qs)
        row = next(c for c in summary.category_breakdown if c.category == "Consulting")
        self.assertEqual(row.net, Decimal("1500.00"))


# Service: Monthly Report

class DashboardServiceMonthlyTest(APITestCase):

    def setUp(self):
        self.user = make_user("monthly@example.com")
        # Jan 2024
        FinancialRecord.objects.create(
            title="Jan Income", amount=Decimal("3000"), category="Salary",
            transaction_type=TransactionType.INCOME,
            date=date(2024, 1, 15), created_by=self.user,
        )
        FinancialRecord.objects.create(
            title="Jan Expense", amount=Decimal("1200"), category="Rent",
            transaction_type=TransactionType.EXPENSE,
            date=date(2024, 1, 20), created_by=self.user,
        )
        # Feb 2024
        FinancialRecord.objects.create(
            title="Feb Income", amount=Decimal("3500"), category="Salary",
            transaction_type=TransactionType.INCOME,
            date=date(2024, 2, 15), created_by=self.user,
        )

    def test_returns_correct_number_of_months(self):
        qs      = FinancialRecord.objects.all()
        monthly = DashboardService.get_monthly_report(qs, limit=12)
        self.assertLessEqual(len(monthly), 12)
        self.assertEqual(len(monthly), 2)   # Only 2 distinct months in test data

    def test_monthly_totals_correct(self):
        qs      = FinancialRecord.objects.all()
        monthly = DashboardService.get_monthly_report(qs, limit=12)
        # Newest month first
        feb = next(m for m in monthly if m.month == 2)
        self.assertEqual(feb.total_income,  Decimal("3500.00"))
        self.assertEqual(feb.total_expense, Decimal("0.00"))

    def test_january_net_balance(self):
        qs      = FinancialRecord.objects.all()
        monthly = DashboardService.get_monthly_report(qs, limit=12)
        jan = next(m for m in monthly if m.month == 1)
        self.assertEqual(jan.net_balance, Decimal("1800.00"))   # 3000 - 1200

    def test_month_names_populated(self):
        qs      = FinancialRecord.objects.all()
        monthly = DashboardService.get_monthly_report(qs, limit=12)
        for m in monthly:
            self.assertNotEqual(m.month_name, "")

    def test_limit_respected(self):
        qs      = FinancialRecord.objects.all()
        monthly = DashboardService.get_monthly_report(qs, limit=1)
        self.assertEqual(len(monthly), 1)


# API Endpoint Tests

class DashboardAPITest(APITestCase):

    def setUp(self):
        self.admin   = make_user("da@example.com", role=Role.ADMIN)
        self.viewer  = make_user("dv@example.com", role=Role.VIEWER)
        self.admin_c  = auth_client(self.admin)
        self.viewer_c = auth_client(self.viewer)
        self.anon_c   = APIClient()

        make_record(self.admin, 5000, TransactionType.INCOME,  category="Salary")
        make_record(self.admin, 2000, TransactionType.EXPENSE, category="Rent")

        self.summary_url = reverse("dashboard-summary")
        self.monthly_url = reverse("dashboard-monthly")
        self.weekly_url = reverse("dashboard-weekly")
        self.recent_url = reverse("dashboard-recent")

    def test_summary_returns_correct_structure(self):
        resp = self.admin_c.get(self.summary_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("total_income",   data)
        self.assertIn("total_expense",  data)
        self.assertIn("net_balance",    data)
        self.assertIn("is_profitable",  data)
        self.assertIn("category_breakdown", data)

    def test_summary_values_correct(self):
        resp = self.admin_c.get(self.summary_url)
        data = resp.data["data"]
        self.assertEqual(Decimal(data["total_income"]),  Decimal("5000.00"))
        self.assertEqual(Decimal(data["total_expense"]), Decimal("2000.00"))
        self.assertEqual(Decimal(data["net_balance"]),   Decimal("3000.00"))
        self.assertTrue(data["is_profitable"])

    def test_viewer_can_access_summary(self):
        resp = self.viewer_c.get(self.summary_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unauthenticated_blocked_from_summary(self):
        resp = self.anon_c.get(self.summary_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_monthly_report_returns_correct_structure(self):
        resp = self.admin_c.get(self.monthly_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("monthly_trends", data)
        self.assertIn("period_months",  data)
        if data["monthly_trends"]:
            entry = data["monthly_trends"][0]
            self.assertIn("year",          entry)
            self.assertIn("month_name",    entry)
            self.assertIn("total_income",  entry)
            self.assertIn("total_expense", entry)
            self.assertIn("net_balance",   entry)

    def test_monthly_report_months_param(self):
        resp = self.admin_c.get(self.monthly_url, {"months": "3"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["period_months"], 3)

    def test_invalid_months_param_rejected(self):
        resp = self.admin_c.get(self.monthly_url, {"months": "notanumber"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_date_filter(self):
        resp = self.admin_c.get(self.summary_url, {
            "date_from": "2030-01-01",  # Future — no records
            "date_to":   "2030-12-31",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertEqual(Decimal(data["total_income"]),  Decimal("0.00"))
        self.assertEqual(Decimal(data["total_expense"]), Decimal("0.00"))

    def test_invalid_date_format_rejected(self):
        resp = self.admin_c.get(self.summary_url, {"date_from": "01-13-2024"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weekly_report_returns_structure(self):
        resp = self.admin_c.get(self.weekly_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("weekly_trends", data)
        self.assertIn("period_weeks", data)

    def test_recent_activity_returns_structure(self):
        resp = self.admin_c.get(self.recent_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("items", data)
        self.assertGreaterEqual(len(data["items"]), 1)

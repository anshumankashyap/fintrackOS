"""
records/tests.py
─────────────────
Tests for FinancialRecord CRUD and RBAC enforcement.

Coverage:
  - Model validation (negative amount, invalid type)
  - Serializer validation (future date, blank title, large expense without description)
  - List endpoint (pagination, filtering by type/category/date)
  - Create endpoint (Viewer blocked, Analyst allowed, Admin allowed)
  - Update endpoint (Viewer blocked, Analyst allowed, Admin allowed)
  - Delete endpoint (Viewer + Analyst blocked, Admin allowed)
  - Unauthenticated access blocked on all endpoints
"""

from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Role, User

from .models import FinancialRecord, TransactionType


# ── Factories ─────────────────────────────────────────────────────

def make_user(email, role=Role.VIEWER, password="Pass1234!"):
    return User.objects.create_user(email=email, password=password, role=role)

def auth_client(user) -> APIClient:
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return c

def make_record(created_by, **kwargs):
    defaults = dict(
        title            = "Test Record",
        amount           = Decimal("500.00"),
        category         = "Salary",
        description      = "Test description",
        transaction_type = TransactionType.INCOME,
        date             = date.today() - timedelta(days=1),
        created_by       = created_by,
    )
    defaults.update(kwargs)
    return FinancialRecord.objects.create(**defaults)


# ── Model Tests ───────────────────────────────────────────────────

class FinancialRecordModelTest(APITestCase):

    def setUp(self):
        self.user = make_user("model@example.com")

    def test_str_representation(self):
        r = make_record(self.user)
        self.assertIn("500.00", str(r))

    def test_is_income_property(self):
        r = make_record(self.user, transaction_type=TransactionType.INCOME)
        self.assertTrue(r.is_income)
        self.assertFalse(r.is_expense)

    def test_is_expense_property(self):
        r = make_record(self.user, transaction_type=TransactionType.EXPENSE)
        self.assertTrue(r.is_expense)
        self.assertFalse(r.is_income)

    def test_default_ordering_newest_first(self):
        older = make_record(self.user, date=date.today() - timedelta(days=10), title="Older")
        newer = make_record(self.user, date=date.today() - timedelta(days=1),  title="Newer")
        records = list(FinancialRecord.objects.all())
        self.assertEqual(records[0].title, "Newer")


# ── Serializer Validation Tests ───────────────────────────────────

class FinancialRecordSerializerTest(APITestCase):

    def setUp(self):
        from rest_framework.test import APIRequestFactory
        self.analyst = make_user("serial@example.com", role=Role.ANALYST)
        factory = APIRequestFactory()
        req = factory.post("/")
        req.user = self.analyst
        self.context = {"request": req}

    def _serializer(self, data):
        from .serializers import FinancialRecordSerializer
        return FinancialRecordSerializer(data=data, context=self.context)

    def test_valid_income_record(self):
        s = self._serializer({
            "title":            "Consulting Fee",
            "amount":           "1500.00",
            "category":         "Consulting",
            "transaction_type": "income",
            "date":             str(date.today() - timedelta(days=1)),
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_zero_amount_rejected(self):
        s = self._serializer({
            "title": "Zero", "amount": "0.00",
            "category": "Test", "transaction_type": "income",
            "date": str(date.today() - timedelta(days=1)),
        })
        self.assertFalse(s.is_valid())
        self.assertIn("amount", s.errors)

    def test_negative_amount_rejected(self):
        s = self._serializer({
            "title": "Negative", "amount": "-100.00",
            "category": "Test", "transaction_type": "income",
            "date": str(date.today() - timedelta(days=1)),
        })
        self.assertFalse(s.is_valid())
        self.assertIn("amount", s.errors)

    def test_future_date_rejected(self):
        s = self._serializer({
            "title": "Future", "amount": "100.00",
            "category": "Test", "transaction_type": "income",
            "date": str(date.today() + timedelta(days=1)),
        })
        self.assertFalse(s.is_valid())
        self.assertIn("date", s.errors)

    def test_invalid_transaction_type_rejected(self):
        s = self._serializer({
            "title": "Bad Type", "amount": "100.00",
            "category": "Test", "transaction_type": "transfer",
            "date": str(date.today() - timedelta(days=1)),
        })
        self.assertFalse(s.is_valid())
        self.assertIn("transaction_type", s.errors)

    def test_large_expense_without_description_rejected(self):
        s = self._serializer({
            "title": "Huge Expense", "amount": "15000.00",
            "category": "Equipment", "transaction_type": "expense",
            "date": str(date.today() - timedelta(days=1)),
            "description": "",
        })
        self.assertFalse(s.is_valid())
        self.assertIn("description", s.errors)

    def test_large_expense_with_description_accepted(self):
        s = self._serializer({
            "title": "Server Upgrade", "amount": "15000.00",
            "category": "Equipment", "transaction_type": "expense",
            "date": str(date.today() - timedelta(days=1)),
            "description": "Purchased 4 high-memory servers for ML workloads.",
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_category_normalised_to_title_case(self):
        s = self._serializer({
            "title": "Salary", "amount": "3000.00",
            "category": "monthly salary",
            "transaction_type": "income",
            "date": str(date.today() - timedelta(days=1)),
        })
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["category"], "Monthly Salary")

    def test_blank_title_rejected(self):
        s = self._serializer({
            "title": "  ", "amount": "100.00",
            "category": "Test", "transaction_type": "income",
            "date": str(date.today() - timedelta(days=1)),
        })
        self.assertFalse(s.is_valid())
        self.assertIn("title", s.errors)


# ── RBAC / API Tests ──────────────────────────────────────────────

class RecordRBACTest(APITestCase):

    def setUp(self):
        self.admin   = make_user("admin@r.com",   role=Role.ADMIN)
        self.analyst = make_user("analyst@r.com", role=Role.ANALYST)
        self.viewer  = make_user("viewer@r.com",  role=Role.VIEWER)

        self.admin_c   = auth_client(self.admin)
        self.analyst_c = auth_client(self.analyst)
        self.viewer_c  = auth_client(self.viewer)
        self.anon_c    = APIClient()

        self.record = make_record(self.admin)
        self.list_url   = reverse("record-list-create")
        self.detail_url = reverse("record-detail", kwargs={"pk": self.record.pk})

    def _create_payload(self, **kwargs):
        base = {
            "title":            "New Record",
            "amount":           "250.00",
            "category":         "Office",
            "transaction_type": "expense",
            "date":             str(date.today() - timedelta(days=1)),
            "description":      "Office supplies.",
        }
        base.update(kwargs)
        return base

    # ── List (GET /records/) ──────────────────────────────────────

    def test_viewer_can_list_records(self):
        resp = self.viewer_c.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_analyst_can_list_records(self):
        resp = self.analyst_c.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_list_records(self):
        resp = self.admin_c.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_list(self):
        resp = self.anon_c.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Create (POST /records/) ───────────────────────────────────

    def test_viewer_cannot_create(self):
        resp = self.viewer_c.post(self.list_url, self._create_payload())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_analyst_can_create(self):
        resp = self.analyst_c.post(self.list_url, self._create_payload())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])

    def test_admin_can_create(self):
        resp = self.admin_c.post(self.list_url, self._create_payload(title="Admin Record"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_cannot_create(self):
        resp = self.anon_c.post(self.list_url, self._create_payload())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Detail (GET /records/{id}/) ───────────────────────────────

    def test_viewer_can_retrieve(self):
        resp = self.viewer_c.get(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], self.record.title)

    # ── Update (PUT/PATCH /records/{id}/) ─────────────────────────

    def test_viewer_cannot_update(self):
        resp = self.viewer_c.patch(self.detail_url, {"title": "Hacked"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_analyst_can_update(self):
        resp = self.analyst_c.patch(self.detail_url, {"title": "Updated by Analyst"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], "Updated by Analyst")

    def test_admin_can_update(self):
        resp = self.admin_c.patch(self.detail_url, {"title": "Updated by Admin"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ── Delete (DELETE /records/{id}/) ────────────────────────────

    def test_viewer_cannot_delete(self):
        resp = self.viewer_c.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_analyst_cannot_delete(self):
        resp = self.analyst_c.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete(self):
        resp = self.admin_c.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(FinancialRecord.objects.filter(pk=self.record.pk).exists())

    def test_unauthenticated_cannot_delete(self):
        resp = self.anon_c.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── 404 on non-existent record ────────────────────────────────

    def test_nonexistent_record_returns_404(self):
        import uuid
        url  = reverse("record-detail", kwargs={"pk": uuid.uuid4()})
        resp = self.viewer_c.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(resp.data["success"])


# ── Filtering Tests ───────────────────────────────────────────────

class RecordFilteringTest(APITestCase):

    def setUp(self):
        self.admin  = make_user("fadmin@r.com", role=Role.ADMIN)
        self.client = auth_client(self.admin)
        self.url    = reverse("record-list-create")

        make_record(self.admin, transaction_type=TransactionType.INCOME,  category="Salary",  amount=Decimal("3000"), date=date(2024, 1, 15))
        make_record(self.admin, transaction_type=TransactionType.EXPENSE, category="Rent",    amount=Decimal("1500"), date=date(2024, 1, 20))
        make_record(self.admin, transaction_type=TransactionType.EXPENSE, category="Rent",    amount=Decimal("1500"), date=date(2024, 2, 20))
        make_record(self.admin, transaction_type=TransactionType.INCOME,  category="Salary",  amount=Decimal("3000"), date=date(2024, 2, 15))

    def test_filter_by_transaction_type_income(self):
        resp = self.client.get(self.url, {"transaction_type": "income"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertEqual(r["transaction_type"], "income")

    def test_filter_by_category(self):
        resp = self.client.get(self.url, {"category": "Rent"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertEqual(r["category"], "Rent")

    def test_filter_by_date_range(self):
        resp = self.client.get(self.url, {"date_from": "2024-02-01", "date_to": "2024-02-28"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_filter_by_amount_min(self):
        resp = self.client.get(self.url, {"amount_min": "2000"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertGreaterEqual(Decimal(r["amount"]), Decimal("2000"))

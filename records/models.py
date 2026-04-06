"""
records/models.py
──────────────────
FinancialRecord — the core domain model.

Design decisions:
  - UUID primary key (safe for public APIs)
  - amount stored as Decimal (never float — precision matters for money)
  - transaction_type uses TextChoices for DB-level integrity
  - category stored as CharField; allowed labels are CATEGORY_CHOICES (validated in serializer, case-insensitive)
  - created_by FK required (PROTECT) — every record has an owner
  - Soft delete via is_deleted (default manager excludes deleted rows)
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TransactionType(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


class FinancialRecordQuerySet(models.QuerySet):
    """QuerySet that can include soft-deleted rows when needed."""

    def active_only(self):
        return self.filter(is_deleted=False)


class FinancialRecordManager(models.Manager):
    """Default manager: non-deleted records only."""

    def get_queryset(self):
        return FinancialRecordQuerySet(self.model, using=self._db).filter(is_deleted=False)


class FinancialRecord(models.Model):
    """
    Single financial transaction record.
    """

    CATEGORY_CHOICES = [
        ("Education", "Education"),
        ("Entertainment", "Entertainment"),
        ("Food & Dining", "Food & Dining"),
        ("Groceries", "Groceries"),
        ("Health", "Health"),
        ("Investments", "Investments"),
        ("Rent", "Rent"),
        ("Salary", "Salary"),
        ("Travel", "Travel"),
        ("Utilities", "Utilities"),
        ("Office", "Office"),
        ("Equipment", "Equipment"),
        ("Consulting", "Consulting"),
        ("Other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=50,
        help_text="Short title for the transaction.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"), message="Amount must be greater than zero.")],
        help_text="Transaction amount. Must be positive.",
    )
    # Allowed values enforced in FinancialRecordSerializer (see CATEGORY_CHOICES)
    category = models.CharField(max_length=100, db_index=True)
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional notes or context about the transaction.",
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        db_index=True,
        help_text="Whether this is income or an expense.",
    )
    date = models.DateField(
        db_index=True,
        help_text="The date the transaction occurred (YYYY-MM-DD).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financial_records",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FinancialRecordManager()
    all_records = models.Manager()

    class Meta:
        db_table = "financial_records"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["category"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["created_by", "date"]),
            models.Index(fields=["transaction_type", "date"]),
            models.Index(fields=["created_by", "is_deleted"]),
        ]
        verbose_name = "Financial Record"
        verbose_name_plural = "Financial Records"

    def __str__(self):
        sign = "+" if self.transaction_type == TransactionType.INCOME else "-"
        return f"{sign}{self.amount} | {self.title} ({self.date})"

    @property
    def is_income(self) -> bool:
        return self.transaction_type == TransactionType.INCOME

    @property
    def is_expense(self) -> bool:
        return self.transaction_type == TransactionType.EXPENSE

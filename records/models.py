"""
records/models.py
──────────────────
FinancialRecord — the core domain model.

Design decisions:
  - UUID primary key (safe for public APIs)
  - amount stored as Decimal (never float — precision matters for money)
  - transaction_type uses TextChoices for DB-level integrity
  - category stored as free-text CharField (flexible; can be constrained later)
  - created_by FK with PROTECT (deleting a user doesn't wipe their records)
  - Indexes on date, category, transaction_type for fast dashboard queries
"""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TransactionType(models.TextChoices):
    INCOME  = "income",  "Income"
    EXPENSE = "expense", "Expense"


class FinancialRecord(models.Model):
    """
    Single financial transaction record.

    Fields:
        id               — UUID PK
        title            — short description (e.g. "Consulting Invoice #42")
        amount           — positive decimal, max 12 digits, 2 decimal places
        category         — user-defined label (e.g. "Salary", "Rent", "Travel")
        description      — optional long-form notes
        transaction_type — income | expense
        date             — the date the transaction occurred (not created_at)
        created_by       — FK to the user who entered this record
        created_at       — auto-set on insert
        updated_at       — auto-updated on every save
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=255,
        help_text="Short title for the transaction.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01, message="Amount must be greater than zero.")],
        help_text="Transaction amount. Must be positive.",
    )
    category = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Free-text category label (e.g. Salary, Rent, Travel).",
    )
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
        on_delete=models.PROTECT,       # Never lose records when a user is deleted
        related_name="financial_records",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = "financial_records"
        ordering  = ["-date", "-created_at"]
        indexes   = [
            models.Index(fields=["date"]),
            models.Index(fields=["category"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["created_by", "date"]),
            # Composite index for the most common dashboard query
            models.Index(fields=["transaction_type", "date"]),
        ]
        verbose_name        = "Financial Record"
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

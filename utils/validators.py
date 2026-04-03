"""
utils/validators.py
────────────────────
Reusable field validators used across multiple serializers.
Import these into any serializer that needs shared validation logic.

Usage:
    from utils.validators import validate_positive_amount, validate_not_future_date

    class MySerializer(serializers.Serializer):
        amount = serializers.DecimalField(validators=[validate_positive_amount])
        date   = serializers.DateField(validators=[validate_not_future_date])
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError


def validate_positive_amount(value):
    """Reject zero or negative monetary amounts."""
    if value is not None and Decimal(str(value)) <= Decimal("0"):
        raise ValidationError(
            "Amount must be greater than zero. Negative amounts are not allowed."
        )


def validate_not_future_date(value):
    """Reject dates in the future."""
    if value and value > date.today():
        raise ValidationError(
            f"Date cannot be in the future. Today is {date.today().isoformat()}."
        )


def validate_transaction_type(value):
    """Reject transaction types other than 'income' or 'expense'."""
    allowed = {"income", "expense"}
    if value and value.lower() not in allowed:
        raise ValidationError(
            f"Invalid transaction type '{value}'. Must be one of: income, expense."
        )


def sanitize_string(value: str) -> str:
    """
    Strip leading/trailing whitespace and collapse internal runs of
    whitespace to a single space.  Returns empty string for None input.

    Example:
        sanitize_string("  hello   world  ") -> "hello world"
    """
    if not value:
        return ""
    import re
    return re.sub(r"\s+", " ", value.strip())
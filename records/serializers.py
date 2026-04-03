"""
records/serializers.py
───────────────────────
Serializers for the FinancialRecord model.

  FinancialRecordSerializer      — full read/write (create + update)
  FinancialRecordListSerializer  — lightweight list view (no description)
"""

from datetime import date

from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import FinancialRecord, TransactionType


class FinancialRecordSerializer(serializers.ModelSerializer):
    """
    Full serializer — used for create, retrieve, and update.

    Validation rules:
      - amount must be > 0
      - transaction_type must be 'income' or 'expense'
      - date cannot be more than 10 years in the past
      - date cannot be in the future
      - title and category are stripped of leading/trailing whitespace
    """

    # Nested read-only creator info
    created_by_detail = UserSerializer(source="created_by", read_only=True)

    class Meta:
        model  = FinancialRecord
        fields = [
            "id",
            "title",
            "amount",
            "category",
            "description",
            "transaction_type",
            "date",
            "created_by",
            "created_by_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_detail", "created_at", "updated_at"]
        extra_kwargs = {
            "description": {"required": False, "default": ""},
        }

    # ── Field-level validation ────────────────────────────────────

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero. Negative amounts are not allowed."
            )
        if value > 999_999_999_999.99:
            raise serializers.ValidationError("Amount exceeds the maximum allowed value.")
        return value

    def validate_transaction_type(self, value):
        valid = [t.value for t in TransactionType]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid transaction type '{value}'. Must be one of: {', '.join(valid)}."
            )
        return value

    def validate_date(self, value):
        today = date.today()
        # Reject future dates
        if value > today:
            raise serializers.ValidationError(
                f"Transaction date cannot be in the future. Today is {today}."
            )
        # Reject dates more than 10 years old (configurable)
        from dateutil.relativedelta import relativedelta
        oldest_allowed = today - relativedelta(years=10)
        if value < oldest_allowed:
            raise serializers.ValidationError(
                f"Transaction date cannot be more than 10 years in the past."
            )
        return value

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.")
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value

    def validate_category(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Category cannot be blank.")
        return value.title()   # Normalise capitalisation: "travel" → "Travel"

    # ── Cross-field validation ─────────────────────────────────────

    def validate(self, attrs):
        # Example cross-field rule: large single expenses need a description
        if (
            attrs.get("transaction_type") == TransactionType.EXPENSE
            and attrs.get("amount", 0) > 10_000
            and not attrs.get("description", "").strip()
        ):
            raise serializers.ValidationError({
                "description": (
                    "A description is required for expenses exceeding 10,000. "
                    "Please provide context for this transaction."
                )
            })
        return attrs

    def create(self, validated_data):
        # Inject the requesting user as creator
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class FinancialRecordListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list endpoints — omits description and
    nested user object to keep response payloads small.
    """
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model  = FinancialRecord
        fields = [
            "id",
            "title",
            "amount",
            "category",
            "transaction_type",
            "date",
            "created_by_email",
            "created_at",
        ]

"""
records/serializers.py
───────────────────────
Serializers for the FinancialRecord model.
"""

from datetime import date

from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import FinancialRecord, TransactionType


class FinancialRecordSerializer(serializers.ModelSerializer):
    """
    Full serializer — used for create, retrieve, and update (Admin only via RBAC).
    """

    created_by_detail = UserSerializer(source="created_by", read_only=True)

    class Meta:
        model = FinancialRecord
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
        if value > today:
            raise serializers.ValidationError(
                f"Transaction date cannot be in the future. Today is {today}."
            )
        from dateutil.relativedelta import relativedelta

        oldest_allowed = today - relativedelta(years=10)
        if value < oldest_allowed:
            raise serializers.ValidationError(
                "Transaction date cannot be more than 10 years in the past."
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
        raw = (value or "").strip()
        if not raw:
            raise serializers.ValidationError("Category cannot be blank.")
        allowed = {c[0] for c in FinancialRecord.CATEGORY_CHOICES}
        for choice, _ in FinancialRecord.CATEGORY_CHOICES:
            if choice.lower() == raw.lower():
                return choice
        raise serializers.ValidationError(
            f"Invalid category '{raw}'. Must be one of: {', '.join(sorted(allowed))}."
        )

    def validate(self, attrs):
        if self.instance:
            t_type = attrs.get("transaction_type", self.instance.transaction_type)
            amount = attrs.get("amount", self.instance.amount)
            if "description" in attrs:
                description = (attrs.get("description") or "").strip()
            else:
                description = (self.instance.description or "").strip()
        else:
            t_type = attrs.get("transaction_type")
            amount = attrs.get("amount")
            description = (attrs.get("description") or "").strip()

        if (
            t_type == TransactionType.EXPENSE
            and amount is not None
            and amount > 10_000
            and not description
        ):
            raise serializers.ValidationError(
                {
                    "description": (
                        "A description is required for expenses exceeding 10,000. "
                        "Please provide context for this transaction."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class FinancialRecordListSerializer(serializers.ModelSerializer):
    """Lightweight list rows — no description."""

    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = FinancialRecord
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

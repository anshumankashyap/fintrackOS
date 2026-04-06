"""Template context shared across the finance UI."""

from records.models import FinancialRecord


def finance_categories(_request):
    return {"CATEGORY_CHOICES": FinancialRecord.CATEGORY_CHOICES}

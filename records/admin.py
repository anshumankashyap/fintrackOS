"""records/admin.py"""
from django.contrib import admin
from .models import FinancialRecord

@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display  = ["title", "amount", "transaction_type", "category", "date", "created_by"]
    list_filter   = ["transaction_type", "category", "date"]
    search_fields = ["title", "description", "category"]
    ordering      = ["-date"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields   = ["created_by"]

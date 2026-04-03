"""
records/views.py
─────────────────
Financial record CRUD endpoints.

  POST   /api/v1/records/      — create  (Analyst, Admin)
  GET    /api/v1/records/      — list    (Viewer, Analyst, Admin)
  GET    /api/v1/records/{id}/ — detail  (Viewer, Analyst, Admin)
  PUT    /api/v1/records/{id}/ — update  (Analyst, Admin)
  PATCH  /api/v1/records/{id}/ — partial (Analyst, Admin)
  DELETE /api/v1/records/{id}/ — delete  (Admin only)

All endpoints require JWT authentication.
RBAC is enforced by FinancialRecordPermission.
"""

import logging

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardResultsPagination
from core.responses import created_response, no_content_response, success_response
from permissions.rbac import FinancialRecordPermission

from .filters import FinancialRecordFilter
from .models import FinancialRecord
from .serializers import FinancialRecordListSerializer, FinancialRecordSerializer

logger = logging.getLogger("finance")

_RECORD_LIST_PARAMS = [
    OpenApiParameter("category",         description="Filter by category (case-insensitive)"),
    OpenApiParameter("transaction_type", description="Filter: income | expense"),
    OpenApiParameter("date_from",        description="Start date (YYYY-MM-DD)"),
    OpenApiParameter("date_to",          description="End date (YYYY-MM-DD)"),
    OpenApiParameter("amount_min",       description="Minimum amount"),
    OpenApiParameter("amount_max",       description="Maximum amount"),
    OpenApiParameter("search",           description="Search title, description, category"),
    OpenApiParameter("ordering",         description="Sort field (e.g. -date, amount)"),
    OpenApiParameter("page",             description="Page number"),
    OpenApiParameter("page_size",        description="Results per page (max 100)"),
]


@extend_schema(tags=["Records"])
class FinancialRecordListCreateView(APIView):
    """
    GET  — list all financial records (paginated, filterable)
    POST — create a new financial record
    """
    permission_classes = [IsAuthenticated, FinancialRecordPermission]
    pagination_class = StandardResultsPagination
    filterset_class = FinancialRecordFilter

    def _get_filtered_queryset(self, request):
        qs = FinancialRecord.objects.select_related("created_by").all()
        filterset = FinancialRecordFilter(request.query_params, queryset=qs)
        if not filterset.is_valid():
            return qs, filterset.errors
        # Ordering
        ordering = request.query_params.get("ordering", "-date")
        allowed  = ["date", "-date", "amount", "-amount", "created_at", "-created_at", "category", "-category"]
        if ordering in allowed:
            qs = filterset.qs.order_by(ordering)
        else:
            qs = filterset.qs
        return qs, None

    @extend_schema(parameters=_RECORD_LIST_PARAMS)
    def get(self, request):
        qs, errors = self._get_filtered_queryset(request)
        if errors:
            return Response(
                {"success": False, "message": "Invalid filter parameters.", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = FinancialRecordListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = FinancialRecordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        # Invalidate dashboard cache so summaries stay fresh
        cache.delete_pattern("finance:dashboard:*") if hasattr(cache, "delete_pattern") else None
        logger.info("Record created: %s by %s", record.id, request.user.email)
        return created_response(
            data=FinancialRecordSerializer(record, context={"request": request}).data,
            message="Financial record created successfully.",
        )


@extend_schema(tags=["Records"])
class FinancialRecordDetailView(APIView):
    """
    GET    — retrieve a single record
    PUT    — full update
    PATCH  — partial update
    DELETE — delete (Admin only — enforced by FinancialRecordPermission)
    """
    permission_classes = [IsAuthenticated, FinancialRecordPermission]

    def _get_record(self, pk):
        try:
            return FinancialRecord.objects.select_related("created_by").get(pk=pk)
        except FinancialRecord.DoesNotExist:
            from core.exceptions import FinancialRecordNotFound
            raise FinancialRecordNotFound()

    def get(self, request, pk):
        record = self._get_record(pk)
        serializer = FinancialRecordSerializer(record, context={"request": request})
        return success_response(data=serializer.data)

    def put(self, request, pk):
        record = self._get_record(pk)
        serializer = FinancialRecordSerializer(
            record, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        cache.delete_pattern("finance:dashboard:*") if hasattr(cache, "delete_pattern") else None
        logger.info("Record updated: %s by %s", updated.id, request.user.email)
        return success_response(
            data=FinancialRecordSerializer(updated, context={"request": request}).data,
            message="Financial record updated successfully.",
        )

    def patch(self, request, pk):
        record = self._get_record(pk)
        serializer = FinancialRecordSerializer(
            record, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        cache.delete_pattern("finance:dashboard:*") if hasattr(cache, "delete_pattern") else None
        logger.info("Record patched: %s by %s", updated.id, request.user.email)
        return success_response(
            data=FinancialRecordSerializer(updated, context={"request": request}).data,
            message="Financial record updated successfully.",
        )

    def delete(self, request, pk):
        record = self._get_record(pk)
        record_id = str(record.id)
        record.delete()
        cache.delete_pattern("finance:dashboard:*") if hasattr(cache, "delete_pattern") else None
        logger.info("Record deleted: %s by admin %s", record_id, request.user.email)
        return no_content_response(message="Financial record deleted successfully.")

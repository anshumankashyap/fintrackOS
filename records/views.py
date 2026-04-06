"""
records/views.py
─────────────────
Financial record CRUD endpoints.

  POST   /api/v1/records/      — create  (Admin)
  GET    /api/v1/records/      — list    (Analyst: own · Admin: all)
  GET    /api/v1/records/{id}/ — detail  (same scope + object rules)
  PUT    /api/v1/records/{id}/ — update  (Admin)
  PATCH  /api/v1/records/{id}/ — partial (Admin)
  DELETE /api/v1/records/{id}/ — soft delete (Admin) → 204 No Content

Viewer role cannot access any /records/ endpoint.
"""

import logging

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardResultsPagination
from core.responses import created_response, empty_no_content_response, success_response
from permissions.rbac import FinancialRecordPermission

from .filters import FinancialRecordFilter
from .models import FinancialRecord
from .serializers import FinancialRecordListSerializer, FinancialRecordSerializer

logger = logging.getLogger("finance")

_RECORD_LIST_PARAMS = [
    OpenApiParameter("category", description="Filter by category (case-insensitive)"),
    OpenApiParameter("transaction_type", description="Filter: income | expense"),
    OpenApiParameter("date_from", description="Start date (YYYY-MM-DD)"),
    OpenApiParameter("date_to", description="End date (YYYY-MM-DD)"),
    OpenApiParameter("amount_min", description="Minimum amount"),
    OpenApiParameter("amount_max", description="Maximum amount"),
    OpenApiParameter("search", description="Search title, description, category"),
    OpenApiParameter("ordering", description="Sort field (e.g. -date, amount)"),
    OpenApiParameter("page", description="Page number"),
    OpenApiParameter("page_size", description="Results per page (max 100)"),
]


def _scoped_queryset(request):
    """Analysts see only their records; Admins see all non-deleted (default manager)."""
    qs = FinancialRecord.objects.select_related("created_by")
    if not request.user.is_admin:
        qs = qs.filter(created_by=request.user)
    return qs


@extend_schema(tags=["Records"])
class FinancialRecordListCreateView(APIView):
    permission_classes = [IsAuthenticated, FinancialRecordPermission]
    pagination_class = StandardResultsPagination
    filterset_class = FinancialRecordFilter

    def _get_filtered_queryset(self, request):
        qs = _scoped_queryset(request)
        filterset = FinancialRecordFilter(request.query_params, queryset=qs)
        if not filterset.is_valid():
            return qs, filterset.errors
        ordering = request.query_params.get("ordering", "-date")
        allowed = [
            "date",
            "-date",
            "amount",
            "-amount",
            "created_at",
            "-created_at",
            "category",
            "-category",
        ]
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
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("finance:dashboard:*")
        logger.info("Record created: %s by %s", record.id, request.user.email)
        return created_response(
            data=FinancialRecordSerializer(record, context={"request": request}).data,
            message="Financial record created successfully.",
        )


@extend_schema(tags=["Records"])
class FinancialRecordDetailView(APIView):
    permission_classes = [IsAuthenticated, FinancialRecordPermission]

    def _get_record(self, request, pk):
        try:
            record = _scoped_queryset(request).get(pk=pk)
        except FinancialRecord.DoesNotExist:
            from core.exceptions import FinancialRecordNotFound

            raise FinancialRecordNotFound()
        self.check_object_permissions(request, record)
        return record

    def get(self, request, pk):
        record = self._get_record(request, pk)
        serializer = FinancialRecordSerializer(record, context={"request": request})
        return success_response(data=serializer.data)

    def put(self, request, pk):
        record = self._get_record(request, pk)
        serializer = FinancialRecordSerializer(
            record, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("finance:dashboard:*")
        logger.info("Record updated: %s by %s", updated.id, request.user.email)
        return success_response(
            data=FinancialRecordSerializer(updated, context={"request": request}).data,
            message="Financial record updated successfully.",
        )

    def patch(self, request, pk):
        record = self._get_record(request, pk)
        serializer = FinancialRecordSerializer(
            record, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("finance:dashboard:*")
        logger.info("Record patched: %s by %s", updated.id, request.user.email)
        return success_response(
            data=FinancialRecordSerializer(updated, context={"request": request}).data,
            message="Financial record updated successfully.",
        )

    def delete(self, request, pk):
        record = self._get_record(request, pk)
        record_id = str(record.id)
        record.is_deleted = True
        record.save(update_fields=["is_deleted", "updated_at"])
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("finance:dashboard:*")
        logger.info("Record soft-deleted: %s by admin %s", record_id, request.user.email)
        return empty_no_content_response()

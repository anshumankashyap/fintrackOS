"""
core/exceptions.py
───────────────────
Centralised exception handling.

Django REST Framework calls `custom_exception_handler` for every
unhandled exception in a view.  We normalise all error responses to:

    {
        "success": false,
        "code":    "PERMISSION_DENIED",
        "message": "Human-readable description",
        "errors":  { ... field-level detail (optional) ... }
    }
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("finance")


# Custom Exception Classes

class BusinessLogicError(APIException):
    """Raised when business rules are violated (e.g. invalid state transition)."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Business logic error."
    default_code = "BUSINESS_LOGIC_ERROR"


class ResourceConflict(APIException):
    """Raised when a resource already exists (e.g. duplicate email)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict."
    default_code = "RESOURCE_CONFLICT"


class FinancialRecordNotFound(NotFound):
    default_detail = "Financial record not found."
    default_code = "RECORD_NOT_FOUND"


# Error-code map

_CODE_MAP = {
    "authentication_failed":   "AUTHENTICATION_FAILED",
    "not_authenticated":       "NOT_AUTHENTICATED",
    "permission_denied":       "PERMISSION_DENIED",
    "not_found":               "NOT_FOUND",
    "throttled":               "RATE_LIMIT_EXCEEDED",
    "invalid":                 "VALIDATION_ERROR",
    "BUSINESS_LOGIC_ERROR":    "BUSINESS_LOGIC_ERROR",
    "RESOURCE_CONFLICT":       "RESOURCE_CONFLICT",
}


def _get_code(exc) -> str:
    if hasattr(exc, "default_code"):
        code = exc.default_code
        return _CODE_MAP.get(code, code.upper())
    return "ERROR"


def _flatten_errors(detail):
    """
    Recursively flatten DRF validation error detail into a dict of
    field → [list of messages].
    """
    if isinstance(detail, list):
        return [str(item) for item in detail]
    if isinstance(detail, dict):
        return {key: _flatten_errors(val) for key, val in detail.items()}
    return str(detail)


def custom_exception_handler(exc, context):
    """
    Global DRF exception handler.

    Converts Django's native exceptions → DRF equivalents, then
    normalises every error response into a consistent JSON envelope.
    """
    # Convert Django's own exceptions to DRF equivalents
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=exc.messages)
    elif isinstance(exc, PermissionDenied):
        exc = DRFPermissionDenied()

    # Let DRF handle it first (sets response.data)
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled server error — log it and return 500
        logger.exception("Unhandled server error", exc_info=exc)
        return Response(
            {
                "success": False,
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Build normalised payload
    code = _get_code(exc)
    errors = None

    if isinstance(exc, ValidationError):
        message = "Input validation failed."
        errors = _flatten_errors(exc.detail)
    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        message = "Authentication required. Please provide a valid Bearer token."
    elif isinstance(exc, (DRFPermissionDenied,)):
        message = "You do not have permission to perform this action."
    elif isinstance(exc, NotFound):
        message = str(exc.detail) if hasattr(exc, "detail") else "Resource not found."
    elif isinstance(exc, Throttled):
        wait = getattr(exc, "wait", None)
        message = f"Rate limit exceeded. Try again in {int(wait)} seconds." if wait else "Rate limit exceeded."
    else:
        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)

    payload = {
        "success": False,
        "code": code,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors

    response.data = payload
    return response

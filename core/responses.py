"""
core/responses.py
──────────────────
Helper functions for consistent API response envelopes.
"""

from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK, **kwargs):
    payload = {
        "success": True,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return Response(payload, status=status_code)


def created_response(data=None, message="Resource created successfully."):
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def empty_no_content_response():
    """RESTful DELETE success — no body (RFC 9110)."""
    return Response(status=status.HTTP_204_NO_CONTENT)

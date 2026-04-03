"""
core/responses.py
──────────────────
Helper functions for consistent API response envelopes.

Every successful response from a view should use one of these helpers
so all endpoints return a uniform structure.
"""

from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK, **kwargs):
    """
    Return a successful JSON response.

        {
            "success": true,
            "message": "...",
            "data": { ... }
        }
    """
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


def no_content_response(message="Resource deleted successfully."):
    return Response({"success": True, "message": message}, status=status.HTTP_200_OK)

"""
core/middleware.py
───────────────────
Request/response logging middleware.
Logs method, path, user, status code, and latency for every request.
"""

import logging
import time

logger = logging.getLogger("finance")


class RequestLoggingMiddleware:
    """Logs every inbound request with timing info."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        user = (
            request.user.email
            if hasattr(request, "user") and request.user.is_authenticated
            else "anonymous"
        )
        logger.info(
            "%s %s | user=%s | status=%d | %.1fms",
            request.method,
            request.path,
            user,
            response.status_code,
            duration_ms,
        )
        return response

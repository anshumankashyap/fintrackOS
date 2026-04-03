"""
utils/decorators.py
────────────────────
Reusable decorators for DRF views.

  @cache_response(timeout)  — cache a view's response in Redis
  @admin_required            — shortcut permission decorator
"""

import functools
import hashlib
import json
import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger("finance")


def cache_response(timeout: int = 300, key_prefix: str = "view"):
    """
    Cache a DRF APIView method's response in Redis.

    The cache key is built from: prefix + user_id + request path + query params.
    This ensures different users and different filter combinations each get
    their own cached entry.

    Usage:
        class MyView(APIView):
            @cache_response(timeout=60, key_prefix="myview")
            def get(self, request):
                ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Build a deterministic cache key
            user_id   = str(request.user.id) if request.user.is_authenticated else "anon"
            param_str = json.dumps(dict(request.query_params), sort_keys=True)
            digest    = hashlib.md5(f"{request.path}{param_str}".encode()).hexdigest()[:10]
            cache_key = f"finance:{key_prefix}:{user_id}:{digest}"

            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s", cache_key)
                return Response(cached)

            response = func(self, request, *args, **kwargs)

            if response.status_code == status.HTTP_200_OK:
                cache.set(cache_key, response.data, timeout=timeout)
                logger.debug("Cache SET: %s (ttl=%ds)", cache_key, timeout)

            return response
        return wrapper
    return decorator


def admin_required(func):
    """
    Decorator that returns 403 immediately if the requesting user is not Admin.
    Use on individual methods inside a view that has mixed role requirements.

    Usage:
        class SomeView(APIView):
            @admin_required
            def delete(self, request, pk):
                ...
    """
    @functools.wraps(func)
    def wrapper(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_admin):
            return Response(
                {"success": False, "code": "PERMISSION_DENIED",
                 "message": "Admin role required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return func(self, request, *args, **kwargs)
    return wrapper
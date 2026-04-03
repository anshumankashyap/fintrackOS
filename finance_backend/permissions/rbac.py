"""
permissions/rbac.py
────────────────────
Role-Based Access Control permission classes.

Each class maps to exactly one role boundary.
Views compose them using DRF's permission_classes list.

Role Hierarchy (least → most privileged):
  VIEWER  → read-only
  ANALYST → read + create + update
  ADMIN   → full access + user management

Usage in views:
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    permission_classes = [IsAuthenticated, IsAdmin]
    permission_classes = [IsAuthenticated, IsViewerOrAbove]  # any auth'd user
"""

from rest_framework.permissions import BasePermission

from accounts.models import Role


# ── Base helper ───────────────────────────────────────────────────

class _RolePermission(BasePermission):
    """Internal base — subclasses declare `allowed_roles`."""
    allowed_roles: list = []
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return (
            bool(request.user and request.user.is_authenticated)
            and request.user.role in self.allowed_roles
        )


# ── Concrete Permission Classes ───────────────────────────────────

class IsAdmin(BasePermission):
    """
    Grants access **only** to users with the Admin role.
    Used for: user management, role assignment, delete operations.
    """
    message = "Admin role required."

    def has_permission(self, request, view):
        return (
            bool(request.user and request.user.is_authenticated)
            and request.user.is_admin
        )


class IsAnalystOrAbove(_RolePermission):
    """
    Grants access to Analysts **and** Admins.
    Used for: creating and updating financial records.
    """
    allowed_roles = [Role.ANALYST, Role.ADMIN]
    message = "Analyst or Admin role required."


class IsViewerOrAbove(_RolePermission):
    """
    Grants access to any authenticated user (Viewer, Analyst, or Admin).
    Used for: read endpoints that require authentication.
    """
    allowed_roles = [Role.VIEWER, Role.ANALYST, Role.ADMIN]
    message = "Authentication required."


# ── Object-level permission ────────────────────────────────────────

class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: grants access if the user created the
    resource, or if the user is an Admin.

    Views must call self.check_object_permissions(request, obj)
    to trigger object-level checks.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        # Expect obj to have a `created_by` FK to User
        return getattr(obj, "created_by_id", None) == request.user.id


# ── Financial Record permission matrix ────────────────────────────

class FinancialRecordPermission(BasePermission):
    """
    Enforces the full permission matrix for financial records:

        Action          Viewer    Analyst   Admin
        ─────────────────────────────────────────
        list / retrieve   ✅        ✅        ✅
        create            ❌        ✅        ✅
        update / partial  ❌        ✅        ✅
        destroy           ❌        ❌        ✅
    """
    message = "You do not have permission to perform this action on financial records."

    # Map HTTP methods to minimum required role
    _METHOD_ROLES = {
        "GET":    [Role.VIEWER,  Role.ANALYST, Role.ADMIN],
        "HEAD":   [Role.VIEWER,  Role.ANALYST, Role.ADMIN],
        "OPTIONS":[Role.VIEWER,  Role.ANALYST, Role.ADMIN],
        "POST":   [Role.ANALYST, Role.ADMIN],
        "PUT":    [Role.ANALYST, Role.ADMIN],
        "PATCH":  [Role.ANALYST, Role.ADMIN],
        "DELETE": [Role.ADMIN],
    }

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        allowed = self._METHOD_ROLES.get(request.method, [])
        return request.user.role in allowed

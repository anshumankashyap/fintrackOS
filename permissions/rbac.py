"""
permissions/rbac.py
────────────────────
Role-Based Access Control permission classes.

Assignment matrix:
  Viewer   — dashboard APIs only (no /records/)
  Analyst  — read financial records (own data) + dashboard analytics (own data)
  Admin    — full CRUD on records (see all data) + user management

Views compose permission classes using DRF's permission_classes list.
"""

from rest_framework.permissions import BasePermission

from accounts.models import Role


class _RolePermission(BasePermission):
    """Internal base — subclasses declare `allowed_roles`."""
    allowed_roles: list = []
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return (
            bool(request.user and request.user.is_authenticated)
            and request.user.role in self.allowed_roles
        )


class IsAdmin(BasePermission):
    """
    Grants access only to Admin role.
    User management and record mutations (create/update/delete).
    """
    message = "Admin role required."

    def has_permission(self, request, view):
        return (
            bool(request.user and request.user.is_authenticated)
            and request.user.is_admin
        )


class CanAccessDashboard(_RolePermission):
    """
    Viewer, Analyst, and Admin may access dashboard analytics endpoints.
    """
    allowed_roles = [Role.VIEWER, Role.ANALYST, Role.ADMIN]
    message = "You do not have permission to access the dashboard."


class IsAnalystOrAdmin(_RolePermission):
    """Analyst or Admin — read-only access to financial record APIs."""
    allowed_roles = [Role.ANALYST, Role.ADMIN]
    message = "Analyst or Admin role required to access financial records."


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level: user owns the record (created_by) or is Admin.
    Used for read/update/delete on a single FinancialRecord instance.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        return getattr(obj, "created_by_id", None) == request.user.id


class FinancialRecordPermission(BasePermission):
    """
    Financial records API matrix (assignment-aligned):

        Action           Viewer    Analyst    Admin
        ─────────────────────────────────────────────────
        list / retrieve    —         ✅ own     ✅ all
        create             —         —          ✅
        update             —         —          ✅
        delete (soft)      —         —          ✅
    """
    message = "You do not have permission to perform this action on financial records."

    _READ_METHODS = ("GET", "HEAD", "OPTIONS")
    _WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        user = request.user

        if user.role == Role.VIEWER:
            return False

        method = request.method

        if method in self._READ_METHODS:
            return user.role in (Role.ANALYST, Role.ADMIN)

        if method in self._WRITE_METHODS:
            return user.role == Role.ADMIN

        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_admin:
            return True
        if request.user.role == Role.ANALYST:
            return getattr(obj, "created_by_id", None) == request.user.id
        return False

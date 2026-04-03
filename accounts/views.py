"""
accounts/views.py
──────────────────
Auth + user management endpoints.

  POST   /api/v1/auth/register/           — public sign-up
  POST   /api/v1/auth/login/              — obtain JWT pair
  POST   /api/v1/auth/token/refresh/      — refresh access token
  POST   /api/v1/auth/logout/             — blacklist refresh token
  GET    /api/v1/auth/me/                 — own profile
  PATCH  /api/v1/auth/me/                 — update own profile
  POST   /api/v1/auth/change-password/    — change own password
  GET    /api/v1/auth/users/              — list all users (Admin)
  GET    /api/v1/auth/users/{id}/         — get user detail (Admin)
  PATCH  /api/v1/auth/users/{id}/         — update user / assign role (Admin)
  DELETE /api/v1/auth/users/{id}/         — deactivate user (Admin)
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.responses import created_response, no_content_response, success_response
from permissions.rbac import IsAdmin

from .models import User
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

logger = logging.getLogger("finance")


# ── Registration ──────────────────────────────────────────────────

@extend_schema(tags=["Auth"])
class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    New users are always assigned the **Viewer** role.
    An Admin must promote them to Analyst or Admin.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("New user registered: %s", user.email)
        return created_response(
            data=UserSerializer(user).data,
            message="Account created successfully. You have been assigned the Viewer role.",
        )


# ── Login ─────────────────────────────────────────────────────────

@extend_schema(tags=["Auth"])
class LoginView(TokenObtainPairView):
    """
    Authenticate with email + password.
    Returns access token (short-lived) and refresh token (long-lived).
    The access token payload contains: user_id, email, role, full_name.
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = "auth"


# ── Logout ────────────────────────────────────────────────────────

@extend_schema(
    tags=["Auth"],
    request={"application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}},
    responses={200: OpenApiResponse(description="Logged out successfully.")},
)
class LogoutView(APIView):
    """
    Blacklist the provided refresh token.
    After calling this endpoint, the token cannot be used to issue new access tokens.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "message": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            return Response(
                {"success": False, "message": f"Invalid token: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.info("User logged out: %s", request.user.email)
        return success_response(message="Logged out successfully.")


# ── Own Profile ───────────────────────────────────────────────────

@extend_schema(tags=["Auth"])
class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  — retrieve own profile
    PATCH — update own first_name / last_name (email and role are immutable here)
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return success_response(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Profile updated.")


# ── Change Password ───────────────────────────────────────────────

@extend_schema(tags=["Auth"])
class ChangePasswordView(APIView):
    """Change authenticated user's password."""
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Password changed for user: %s", request.user.email)
        return success_response(message="Password changed successfully. Please log in again.")


# ── Admin: User Management ────────────────────────────────────────

@extend_schema(tags=["Users"])
class UserListView(generics.ListAPIView):
    """
    Admin only — list all users with full detail including role.
    Supports filtering by role and searching by email/name.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "email", "role"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        return User.objects.all()


@extend_schema(tags=["Users"])
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin only — retrieve, update, or deactivate a user.
    PATCH  — update profile fields and/or assign a new role
    DELETE — soft-delete (sets is_active=False, does not wipe data)
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return User.objects.all()

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return success_response(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        # Prevent admin from accidentally locking out their own account
        instance = self.get_object()
        if instance == request.user and "role" in request.data:
            if request.data["role"] != "admin":
                return Response(
                    {"success": False, "message": "You cannot remove your own admin role."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="User updated.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response(
                {"success": False, "message": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        logger.info("Admin %s deactivated user %s", request.user.email, instance.email)
        return no_content_response(message=f"User {instance.email} has been deactivated.")

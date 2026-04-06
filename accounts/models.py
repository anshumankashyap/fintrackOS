"""
accounts/models.py
───────────────────
Custom User model extending AbstractBaseUser.

Design decisions:
- Email is the unique identifier (not username)
- Role is stored as a CharField with choices (VIEWER / ANALYST / ADMIN)
- Django's built-in password hashing (PBKDF2-SHA256) is used automatically
- AbstractBaseUser gives us full control over the auth flow
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


# Role Constants

class Role(models.TextChoices):
    VIEWER  = "viewer",  "Viewer"    # Read-only access
    ANALYST = "analyst", "Analyst"   # Create + update records
    ADMIN   = "admin",   "Admin"     # Full access + user management


# Custom Manager

class UserManager(BaseUserManager):
    """
    Custom manager so we can create users with email + password
    instead of Django's default username-based flow.
    """

    def create_user(self, email: str, password: str, role=Role.VIEWER, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)   # Calls Django's PBKDF2 hashing
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, role=Role.ADMIN, **extra_fields)


# User Model

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.

    Fields:
        id          — UUID primary key (no sequential IDs exposed in URLs)
        email       — unique login identifier
        first_name  — given name
        last_name   — family name
        role        — VIEWER | ANALYST | ADMIN
        is_active   — soft-delete / account enable flag
        is_staff    — Django admin access
        date_joined — creation timestamp
        last_login  — updated automatically by SimpleJWT
    """

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email       = models.EmailField(unique=True, db_index=True)
    first_name  = models.CharField(max_length=150, blank=True)
    last_name   = models.CharField(max_length=150, blank=True)
    role        = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
        db_index=True,
    )
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Manager
    objects = UserManager()

    # Auth config
    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table  = "auth_user"
        ordering  = ["-date_joined"]
        verbose_name       = "User"
        verbose_name_plural = "Users"

    # Properties

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    # RBAC helpers (used by permission classes)

    @property
    def is_viewer(self) -> bool:
        return self.role == Role.VIEWER

    @property
    def is_analyst(self) -> bool:
        return self.role == Role.ANALYST

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def has_role(self, *roles) -> bool:
        """Returns True if user's role is one of the given roles."""
        return self.role in roles

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

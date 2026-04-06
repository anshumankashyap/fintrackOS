"""
accounts/serializers.py
────────────────────────
All serializers for the accounts app:

  - UserRegistrationSerializer  — new user sign-up
  - UserSerializer              — read + update profile
  - AdminUserSerializer         — admin view (includes role field)
  - ChangePasswordSerializer    — authenticated password change
  - CustomTokenObtainPairSerializer — injects role into JWT payload
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role, User


# JWT: inject role + name into token payload

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT serializer to embed user role and
    display name in the access token payload.  Downstream services
    can read the role without a DB round-trip.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims — readable in the JWT payload
        token["role"]       = user.role
        token["email"]      = user.email
        token["full_name"]  = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add user info alongside the tokens
        data["user"] = {
            "id":        str(self.user.id),
            "email":     self.user.email,
            "full_name": self.user.full_name,
            "role":      self.user.role,
        }
        return data


# Registration

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Used at POST /api/v1/auth/register/
    Validates email uniqueness, password strength, and password match.
    New users are always created as VIEWER (role escalation goes through Admin).
    """

    password  = serializers.CharField(
        write_only=True, required=True, min_length=8,
        style={"input_type": "password"},
        help_text="Min 8 chars. Must pass Django's password validators.",
    )
    password2 = serializers.CharField(
        write_only=True, required=True,
        style={"input_type": "password"},
        label="Confirm password",
    )

    class Meta:
        model  = User
        fields = ["id", "email", "first_name", "last_name", "password", "password2"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name":  {"required": True},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        # Run Django's built-in password strength validators
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email      = validated_data["email"],
            password   = validated_data["password"],
            first_name = validated_data.get("first_name", ""),
            last_name  = validated_data.get("last_name", ""),
            role       = Role.VIEWER,   # Always default to least privilege
        )


# User Profile

class UserSerializer(serializers.ModelSerializer):
    """
    Read/update own profile — no role field (admins use AdminUserSerializer).
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "date_joined", "last_login",
        ]
        read_only_fields = ["id", "email", "role", "date_joined", "last_login"]


# Admin User View

class AdminUserSerializer(serializers.ModelSerializer):
    """
    Full user view for admins — exposes and allows updating `role`.
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "is_active", "date_joined", "last_login",
        ]
        read_only_fields = ["id", "email", "date_joined", "last_login"]

    def validate_role(self, value):
        if value not in [r.value for r in Role]:
            raise serializers.ValidationError(
                f"Invalid role. Choose from: {', '.join(r.value for r in Role)}."
            )
        return value


# Password Change

class ChangePasswordSerializer(serializers.Serializer):
    """Used at POST /api/v1/auth/change-password/"""

    current_password = serializers.CharField(write_only=True, required=True)
    new_password     = serializers.CharField(write_only=True, required=True, min_length=8)
    new_password2    = serializers.CharField(write_only=True, required=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "New passwords do not match."})
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user

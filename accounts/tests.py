"""
accounts/tests.py
──────────────────
Unit + integration tests for the authentication system.

Coverage:
  - User model (creation, password hashing, role helpers)
  - Registration endpoint (validation, duplicate email, role default)
  - Login endpoint (JWT payload, wrong password, inactive user)
  - Token refresh and logout (blacklisting)
  - Profile (GET /me, PATCH /me, change-password)
  - Admin user management (list, role assignment, deactivation)
"""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Role, User


# ── Factories ─────────────────────────────────────────────────────

def make_user(email="test@example.com", password="StrongPass123!", role=Role.VIEWER, **kwargs):
    return User.objects.create_user(email=email, password=password, role=role, **kwargs)

def make_admin(**kwargs):
    kwargs.setdefault("email", "admin@example.com")
    kwargs.setdefault("password", "AdminPass123!")
    return make_user(role=Role.ADMIN, **kwargs)

def make_analyst(**kwargs):
    kwargs.setdefault("email", "analyst@example.com")
    kwargs.setdefault("password", "AnalystPass123!")
    return make_user(role=Role.ANALYST, **kwargs)

def auth_client(user) -> APIClient:
    """Return an APIClient pre-authenticated with the user's JWT."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ── Model Tests ───────────────────────────────────────────────────

class UserModelTest(APITestCase):

    def test_create_user_hashes_password(self):
        user = make_user(email="hash@example.com")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_default_role_is_viewer(self):
        user = make_user(email="viewer@example.com")
        self.assertEqual(user.role, Role.VIEWER)
        self.assertTrue(user.is_viewer)
        self.assertFalse(user.is_analyst)
        self.assertFalse(user.is_admin)

    def test_full_name_property(self):
        user = make_user(
            email="name@example.com", first_name="Jane", last_name="Doe"
        )
        self.assertEqual(user.full_name, "Jane Doe")

    def test_full_name_fallback_to_email(self):
        user = make_user(email="nofullname@example.com")
        self.assertEqual(user.full_name, "nofullname@example.com")

    def test_has_role_helper(self):
        admin = make_admin(email="adminrole@example.com")
        self.assertTrue(admin.has_role(Role.ADMIN))
        self.assertFalse(admin.has_role(Role.VIEWER, Role.ANALYST))

    def test_superuser_creation(self):
        su = User.objects.create_superuser("su@example.com", "SuperPass123!")
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertEqual(su.role, Role.ADMIN)


# ── Registration Tests ────────────────────────────────────────────

class RegistrationTest(APITestCase):

    def setUp(self):
        self.url = reverse("auth-register")

    def _payload(self, **overrides):
        base = {
            "email":      "newuser@example.com",
            "first_name": "New",
            "last_name":  "User",
            "password":   "StrongPass123!",
            "password2":  "StrongPass123!",
        }
        base.update(overrides)
        return base

    def test_successful_registration(self):
        resp = self.client.post(self.url, self._payload())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])
        # New user is always a Viewer
        self.assertEqual(resp.data["data"]["role"], Role.VIEWER)

    def test_duplicate_email_rejected(self):
        make_user(email="existing@example.com")
        resp = self.client.post(self.url, self._payload(email="existing@example.com"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_mismatch_rejected(self):
        resp = self.client.post(self.url, self._payload(password2="WrongPass999!"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", resp.data.get("errors", {}))

    def test_short_password_rejected(self):
        resp = self.client.post(self.url, self._payload(password="abc", password2="abc"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_email_rejected(self):
        data = self._payload()
        data.pop("email")
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_normalised_to_lowercase(self):
        resp = self.client.post(self.url, self._payload(email="UPPER@EXAMPLE.COM"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["data"]["email"], "upper@example.com")


# ── Login Tests ───────────────────────────────────────────────────

class LoginTest(APITestCase):

    def setUp(self):
        self.url  = reverse("auth-login")
        self.user = make_user(email="login@example.com", password="LoginPass123!", role=Role.ANALYST)

    def test_successful_login_returns_tokens(self):
        resp = self.client.post(self.url, {"email": "login@example.com", "password": "LoginPass123!"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_jwt_payload_contains_role(self):
        import base64, json
        resp = self.client.post(self.url, {"email": "login@example.com", "password": "LoginPass123!"})
        token   = resp.data["access"]
        payload = json.loads(base64.b64decode(token.split(".")[1] + "=="))
        self.assertEqual(payload["role"], Role.ANALYST)

    def test_wrong_password_rejected(self):
        resp = self.client.post(self.url, {"email": "login@example.com", "password": "WrongPass!"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(self.url, {"email": "login@example.com", "password": "LoginPass123!"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_email_rejected(self):
        resp = self.client.post(self.url, {"email": "ghost@example.com", "password": "AnyPass123!"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Logout Tests ──────────────────────────────────────────────────

class LogoutTest(APITestCase):

    def setUp(self):
        self.user    = make_user(email="logout@example.com", password="LogoutPass123!")
        self.client  = auth_client(self.user)
        self.refresh = str(RefreshToken.for_user(self.user))
        self.url     = reverse("auth-logout")

    def test_logout_blacklists_token(self):
        resp = self.client.post(self.url, {"refresh": self.refresh})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_blacklisted_token_cannot_refresh(self):
        self.client.post(self.url, {"refresh": self.refresh})
        refresh_url = reverse("token-refresh")
        resp = APIClient().post(refresh_url, {"refresh": self.refresh})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_token_returns_400(self):
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ── Profile Tests ─────────────────────────────────────────────────

class ProfileTest(APITestCase):

    def setUp(self):
        self.user   = make_user(
            email="profile@example.com", first_name="Alice", last_name="Smith"
        )
        self.client = auth_client(self.user)
        self.url    = reverse("auth-me")

    def test_get_own_profile(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["email"], "profile@example.com")

    def test_update_name(self):
        resp = self.client.patch(self.url, {"first_name": "Bob"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["first_name"], "Bob")

    def test_cannot_change_role_via_me_endpoint(self):
        resp = self.client.patch(self.url, {"role": "admin"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Role should be unchanged
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, Role.VIEWER)

    def test_unauthenticated_access_denied(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordTest(APITestCase):

    def setUp(self):
        self.user   = make_user(email="chpw@example.com", password="OldPass123!")
        self.client = auth_client(self.user)
        self.url    = reverse("auth-change-password")

    def test_successful_password_change(self):
        resp = self.client.post(self.url, {
            "current_password": "OldPass123!",
            "new_password":     "NewPass456!",
            "new_password2":    "NewPass456!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))

    def test_wrong_current_password_rejected(self):
        resp = self.client.post(self.url, {
            "current_password": "WrongOld!",
            "new_password":     "NewPass456!",
            "new_password2":    "NewPass456!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ── Admin User Management Tests ───────────────────────────────────

class AdminUserManagementTest(APITestCase):

    def setUp(self):
        self.admin   = make_admin()
        self.viewer  = make_user(email="v@example.com")
        self.analyst = make_analyst()
        self.admin_client   = auth_client(self.admin)
        self.viewer_client  = auth_client(self.viewer)
        self.list_url       = reverse("user-list")

    def test_admin_can_list_users(self):
        resp = self.admin_client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 3)

    def test_viewer_cannot_list_users(self):
        resp = self.viewer_client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_assign_role(self):
        url  = reverse("user-detail", kwargs={"pk": self.viewer.id})
        resp = self.admin_client.patch(url, {"role": "analyst"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, Role.ANALYST)

    def test_admin_can_deactivate_user(self):
        url  = reverse("user-detail", kwargs={"pk": self.analyst.id})
        resp = self.admin_client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.analyst.refresh_from_db()
        self.assertFalse(self.analyst.is_active)

    def test_admin_cannot_deactivate_self(self):
        url  = reverse("user-detail", kwargs={"pk": self.admin.id})
        resp = self.admin_client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

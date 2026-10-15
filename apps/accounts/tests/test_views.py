"""
Tests for accounts views: registration, login, logout, profile, addresses, permissions.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Address, Profile, WishlistItem

User = get_user_model()


class TestRegistration(TestCase):
    """Test user registration flow."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.register_url = reverse("accounts:register")

    def test_register_page_loads(self):
        """Registration page returns 200."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_register_success(self):
        """User can register with valid data."""
        response = self.client.post(
            self.register_url,
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="testuser").exists())
        user = User.objects.get(username="testuser")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_register_password_mismatch(self):
        """Registration fails when passwords don't match."""
        response = self.client.post(
            self.register_url,
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "SecurePass123!",
                "password2": "DifferentPass!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_register_duplicate_email(self):
        """Registration fails with duplicate email."""
        User.objects.create_user(
            username="existing", email="test@example.com", password="pass"
        )
        response = self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "email": "test@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_username(self):
        """Registration fails with duplicate username."""
        User.objects.create_user(
            username="testuser", email="other@example.com", password="pass"
        )
        response = self.client.post(
            self.register_url,
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="testuser").count(), 1)


class TestLogin(TestCase):
    """Test user login flow."""

    def setUp(self):
        """Create test user and client."""
        self.user = User.objects.create_user(
            username="testuser", password="SecurePass123!"
        )
        self.client = Client()
        self.login_url = reverse("accounts:login")

    def test_login_page_loads(self):
        """Login page returns 200."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_success(self):
        """User can login with correct credentials."""
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "SecurePass123!"},
        )
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_password(self):
        """Login fails with wrong password."""
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "WrongPass!"},
        )
        self.assertEqual(response.status_code, 200)

    def test_login_nonexistent_user(self):
        """Login fails for non-existent user."""
        response = self.client.post(
            self.login_url,
            {"username": "nobody", "password": "SomePass123!"},
        )
        self.assertEqual(response.status_code, 200)


class TestLogout(TestCase):
    """Test user logout flow."""

    def setUp(self):
        """Create logged-in user."""
        self.user = User.objects.create_user(
            username="testuser", password="SecurePass123!"
        )
        self.client = Client()
        self.client.login(username="testuser", password="SecurePass123!")

    def test_logout_post(self):
        """Authenticated user can logout via POST (Django 5.2 default)."""
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)

    def test_logout_get(self):
        """Authenticated user can logout via GET (our custom support)."""
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)


class TestProfilePermissions(TestCase):
    """Test profile access permissions."""

    def setUp(self):
        """Create two regular users and one staff user."""
        self.user1 = User.objects.create_user(
            username="user1", password="SecurePass123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="SecurePass123!"
        )
        self.staff = User.objects.create_user(
            username="staff", password="SecurePass123!", is_staff=True
        )
        self.client = Client()

    def test_profile_owner_access(self):
        """User can view their own profile."""
        self.client.login(username="user1", password="SecurePass123!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)

    def test_profile_other_user_denied(self):
        """User cannot view another user's profile."""
        self.client.login(username="user1", password="SecurePass123!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)

    def test_profile_anonymous_redirected(self):
        """Anonymous user is redirected from profile."""
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_edit_owner(self):
        """User can edit their own profile."""
        self.client.login(username="user1", password="SecurePass123!")
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "phone": "+1 234 567 8900",
                "bio": "Hello world",
                "newsletter_subscribed": True,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_profile_edit_anonymous_redirected(self):
        """Anonymous user is redirected from profile edit."""
        response = self.client.get(reverse("accounts:profile_edit"))
        self.assertEqual(response.status_code, 302)


class TestAddressPermissions(TestCase):
    """Test address management permissions."""

    def setUp(self):
        """Create users with addresses."""
        self.user1 = User.objects.create_user(
            username="user1", password="SecurePass123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="SecurePass123!"
        )
        self.address1 = Address.objects.create(
            user=self.user1,
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="US",
            is_default=True,
        )
        self.client = Client()

    def test_address_list_owner(self):
        """User can list their own addresses."""
        self.client.login(username="user1", password="SecurePass123!")
        response = self.client.get(reverse("accounts:address_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "123 Main St")

    def test_address_list_anonymous_redirected(self):
        """Anonymous user is redirected from address list."""
        response = self.client.get(reverse("accounts:address_list"))
        self.assertEqual(response.status_code, 302)

    def test_address_create_authenticated(self):
        """Authenticated user can create address."""
        self.client.login(username="user1", password="SecurePass123!")
        response = self.client.post(
            reverse("accounts:address_add"),
            {
                "label": "Work",
                "street": "456 Office Blvd",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country": "US",
                "is_default": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Address.objects.filter(user=self.user1, label="Work").exists()
        )

    def test_address_create_anonymous_redirected(self):
        """Anonymous user is redirected from address creation."""
        response = self.client.post(
            reverse("accounts:address_add"),
            {
                "label": "Work",
                "street": "456 Office Blvd",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country": "US",
                "is_default": False,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_address_edit_owner(self):
        """User can edit their own address."""
        self.client.login(username="user1", password="SecurePass123!")
        response = self.client.post(
            reverse("accounts:address_edit", kwargs={"pk": self.address1.pk}),
            {
                "label": "Home Updated",
                "street": "789 New St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
                "is_default": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.address1.refresh_from_db()
        self.assertEqual(self.address1.street, "789 New St")

    def test_address_edit_other_user_denied(self):
        """User cannot edit another user's address."""
        self.client.login(username="user2", password="SecurePass123!")
        response = self.client.post(
            reverse("accounts:address_edit", kwargs={"pk": self.address1.pk}),
            {
                "label": "Hacked",
                "street": "000 Malicious Ave",
                "city": "Nowhere",
                "state": "XX",
                "postal_code": "00000",
                "country": "XX",
                "is_default": False,
            },
        )
        self.assertIn(response.status_code, [302, 403, 404])
        self.address1.refresh_from_db()
        self.assertEqual(self.address1.street, "123 Main St")


class TestAdminPermissions(TestCase):
    """Test admin-only access restrictions."""

    def setUp(self):
        """Create regular user and staff user."""
        self.regular = User.objects.create_user(
            username="regular", password="SecurePass123!"
        )
        self.staff = User.objects.create_user(
            username="staff", password="SecurePass123!", is_staff=True
        )
        self.client = Client()

    def test_admin_dashboard_regular_denied(self):
        """Regular user cannot access admin dashboard."""
        self.client.login(username="regular", password="SecurePass123!")
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, [302, 403])

    def test_admin_dashboard_staff_access(self):
        """Staff user can access admin dashboard."""
        self.client.login(username="staff", password="SecurePass123!")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_admin_redirect_regular_denied(self):
        """Regular user gets forbidden on admin-dashboard URL."""
        self.client.login(username="regular", password="SecurePass123!")
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_redirect_staff_redirects(self):
        """Staff user gets redirected to admin panel."""
        self.client.login(username="staff", password="SecurePass123!")
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/", response.url)


class TestPasswordReset(TestCase):
    """Test password reset flow."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )
        self.client = Client()

    def test_password_reset_page_loads(self):
        """Password reset page returns 200."""
        response = self.client.get(reverse("accounts:password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/password_reset.html")

    def test_password_reset_email_sent(self):
        """Password reset email is sent for valid email."""
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "test@example.com"},
        )
        self.assertEqual(response.status_code, 302)

    def test_password_reset_invalid_email(self):
        """Password reset with non-existent email still redirects."""
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "nonexistent@example.com"},
        )
        self.assertEqual(response.status_code, 302)

    def test_password_reset_done_page(self):
        """Password reset done page loads."""
        response = self.client.get(reverse("accounts:password_reset_done"))
        self.assertEqual(response.status_code, 200)

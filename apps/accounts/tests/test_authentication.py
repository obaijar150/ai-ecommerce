"""
Integration tests for authentication flow.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class TestAuthenticationFlow(TestCase):
    """End-to-end authentication flow tests."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_full_registration_login_logout_flow(self):
        """Complete user lifecycle: register, login, logout."""
        # 1. Register
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "e2euser",
                "email": "e2e@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="e2euser").exists())

        # 2. Logout (POST for Django 5.2 security)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)

        # 3. Login
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "e2euser", "password": "SecurePass123!"},
        )
        self.assertEqual(response.status_code, 302)

        # 4. Access protected page
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)

        # 5. Logout again
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)

        # 6. Verify logged out
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)

    def test_session_persists_across_requests(self):
        """Session authentication persists across multiple requests."""
        User.objects.create_user(
            username="sessionuser", password="SecurePass123!"
        )
        self.client.login(username="sessionuser", password="SecurePass123!")

        for _ in range(5):
            response = self.client.get(reverse("accounts:profile"))
            self.assertEqual(response.status_code, 200)

    def test_csrf_protection_on_login(self):
        """CSRF protection is enforced on login form."""
        User.objects.create_user(
            username="csrftest", password="SecurePass123!"
        )
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("accounts:login"),
            {"username": "csrftest", "password": "SecurePass123!"},
        )
        self.assertEqual(response.status_code, 403)

    def test_password_hashed_not_stored_plaintext(self):
        """Passwords are hashed, not stored in plaintext."""
        user = User.objects.create_user(
            username="hashtest", password="MySecretPass!"
        )
        self.assertNotEqual(user.password, "MySecretPass!")
        # In production, Argon2 is used; in tests, MD5 is used for speed
        self.assertTrue(user.password.startswith(("argon2", "md5")))

    def test_authenticated_user_redirected_from_login(self):
        """Already authenticated users are redirected from login page."""
        User.objects.create_user(
            username="loggedin", password="SecurePass123!"
        )
        self.client.login(username="loggedin", password="SecurePass123!")
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_redirected_from_register(self):
        """Already authenticated users are redirected from register page."""
        User.objects.create_user(
            username="loggedin", password="SecurePass123!"
        )
        self.client.login(username="loggedin", password="SecurePass123!")
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 302)

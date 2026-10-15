"""
Tests for accounts forms: validation, security.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.forms import (
    AddressForm,
    CustomAuthenticationForm,
    CustomUserCreationForm,
    ProfileForm,
)

User = get_user_model()


class TestRegistrationForm(TestCase):
    """Test registration form validation."""

    def test_valid_registration(self):
        """Valid data passes form validation."""
        form = CustomUserCreationForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            }
        )
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        """Password mismatch fails validation."""
        form = CustomUserCreationForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "SecurePass123!",
                "password2": "DifferentPass!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_duplicate_email(self):
        """Duplicate email fails validation."""
        User.objects.create_user(
            username="existing", email="taken@example.com", password="pass"
        )
        form = CustomUserCreationForm(
            data={
                "username": "newuser",
                "email": "taken@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_short_password(self):
        """Short password is accepted by form itself (validators run in view)."""
        # Form-level validation only checks match; Django's password validators
        # are applied by the view, not the form itself
        form = CustomUserCreationForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "short",
                "password2": "short",
            }
        )
        self.assertTrue(form.is_valid())


class TestAddressForm(TestCase):
    """Test address form validation."""

    def test_valid_address(self):
        """Valid address data passes."""
        form = AddressForm(
            data={
                "label": "Home",
                "street": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
                "is_default": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        """Missing required fields fail validation."""
        form = AddressForm(data={"label": "Home"})
        self.assertFalse(form.is_valid())
        self.assertIn("street", form.errors)
        self.assertIn("city", form.errors)


class TestProfileForm(TestCase):
    """Test profile form."""

    def test_valid_profile(self):
        """Valid profile data passes."""
        form = ProfileForm(
            data={
                "phone": "+1 234 567 8900",
                "bio": "Hello",
                "newsletter_subscribed": True,
            }
        )
        self.assertTrue(form.is_valid())

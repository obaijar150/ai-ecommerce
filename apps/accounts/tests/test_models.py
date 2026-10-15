"""
Tests for accounts models.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Address, Profile, WishlistItem
from apps.catalog.models import Product

User = get_user_model()


class TestProfileModel(TestCase):
    """Test Profile model."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser", password="SecurePass123!"
        )

    def test_profile_created_on_user_creation(self):
        """Profile is auto-created when a user is created."""
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_profile_str(self):
        """Profile string representation."""
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(str(profile), "Profile: testuser")


class TestAddressModel(TestCase):
    """Test Address model."""

    def setUp(self):
        """Create test user and address."""
        self.user = User.objects.create_user(
            username="testuser", password="SecurePass123!"
        )

    def test_address_creation(self):
        """Address can be created for user."""
        address = Address.objects.create(
            user=self.user,
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="US",
        )
        self.assertEqual(str(address), "Home: 123 Main St, Springfield")

    def test_address_default_flag(self):
        """Address can be marked as default."""
        address = Address.objects.create(
            user=self.user,
            label="Work",
            street="456 Office Blvd",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="US",
            is_default=True,
        )
        self.assertTrue(address.is_default)


class TestWishlistItemModel(TestCase):
    """Test WishlistItem model."""

    def setUp(self):
        """Create test data."""
        self.user = User.objects.create_user(
            username="testuser", password="SecurePass123!"
        )
        self.product = Product.objects.create(
            name="Test Product",
            description="A test product",
            price=29.99,
            sku="TEST-001",
        )

    def test_wishlist_item_creation(self):
        """Wishlist item can be created."""
        item = WishlistItem.objects.create(user=self.user, product=self.product)
        self.assertEqual(str(item), "testuser wishes for Test Product")

    def test_wishlist_unique_constraint(self):
        """Cannot add same product to wishlist twice."""
        WishlistItem.objects.create(user=self.user, product=self.product)
        with pytest.raises(Exception):
            WishlistItem.objects.create(user=self.user, product=self.product)

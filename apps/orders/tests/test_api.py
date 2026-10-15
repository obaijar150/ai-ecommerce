"""
Tests for the orders DRF API: cart CRUD and the checkout action.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders.models import CartItem, Order

from .factories import AddressFactory, ProductFactory, UserFactory


class TestCartAPI(TestCase):
    """Test the cart API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)
        self.product = ProductFactory(price=Decimal("10.00"), stock_quantity=5)

    def test_cart_requires_auth(self):
        """Anonymous requests are rejected."""
        self.client.force_authenticate(None)
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, 403)

    def test_list_empty_cart(self):
        """A new user has an empty cart."""
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 0)

    def test_add_item(self):
        """Adding an item returns 201 and persists it."""
        response = self.client.post(
            "/api/cart/", {"product": self.product.pk, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_add_beyond_stock_rejected(self):
        """Adding more than stock returns 400."""
        response = self.client.post(
            "/api/cart/", {"product": self.product.pk, "quantity": 99}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_update_quantity(self):
        """Updating a cart line changes the quantity."""
        item = CartItem.objects.create(
            user=self.user, product=self.product, quantity=1
        )
        response = self.client.patch(
            f"/api/cart/{item.pk}/", {"quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

    def test_delete_item(self):
        """Deleting a cart line removes it."""
        item = CartItem.objects.create(
            user=self.user, product=self.product, quantity=1
        )
        response = self.client.delete(f"/api/cart/{item.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())


class TestCheckoutAPI(TestCase):
    """Test the API checkout action."""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)
        self.product = ProductFactory(price=Decimal("10.00"), stock_quantity=5)
        self.address = AddressFactory(user=self.user)

    def test_checkout_requires_address(self):
        """Checkout without a valid address returns 400."""
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        response = self.client.post("/api/cart/checkout/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_creates_paid_order(self):
        """A valid checkout creates a paid order."""
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        response = self.client.post(
            "/api/cart/checkout/",
            {"shipping_address": self.address.pk, "payment_token": "tok_success"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, Decimal("27.59"))

    def test_checkout_empty_cart(self):
        """Checking out an empty cart returns 400."""
        response = self.client.post(
            "/api/cart/checkout/",
            {"shipping_address": self.address.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

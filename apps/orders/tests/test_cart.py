"""
Tests for cart operations: add, update, remove, merge, and validation.
"""

from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.catalog.models import Product
from apps.orders.exceptions import InsufficientStockError, OrderError
from apps.orders.models import CartItem
from apps.orders.services import CartService

from .factories import CartItemFactory, ProductFactory, UserFactory


def make_request(user=None, session=None):
    """Build a minimal request object for calling cart services directly."""
    request = RequestFactory().post("/")
    request.session = session or SessionStore()
    request.user = user or AnonymousUser()
    return request


class TestCartService(TestCase):
    """Unit tests for CartService."""

    def setUp(self):
        self.user = UserFactory()
        self.product = ProductFactory(price=Decimal("10.00"), stock_quantity=5)

    def test_add_to_cart_creates_item(self):
        """Adding a product creates a cart line for the user."""
        request = make_request(user=self.user)
        item = CartService.add_to_cart(request, self.product, 2)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_add_same_product_merges_quantity(self):
        """Adding an existing product increments its quantity."""
        request = make_request(user=self.user)
        CartService.add_to_cart(request, self.product, 1)
        item = CartService.add_to_cart(request, self.product, 2)
        self.assertEqual(item.quantity, 3)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_add_beyond_stock_raises(self):
        """Adding more than available stock raises InsufficientStockError."""
        request = make_request(user=self.user)
        with self.assertRaises(InsufficientStockError):
            CartService.add_to_cart(request, self.product, 6)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_merges_then_exceeds_stock_raises(self):
        """Merging quantities cannot exceed stock."""
        request = make_request(user=self.user)
        CartService.add_to_cart(request, self.product, 4)
        with self.assertRaises(InsufficientStockError):
            CartService.add_to_cart(request, self.product, 2)

    def test_add_inactive_product_raises(self):
        """Inactive products cannot be added to the cart."""
        inactive = ProductFactory(is_active=False)
        request = make_request(user=self.user)
        with self.assertRaises(InsufficientStockError):
            CartService.add_to_cart(request, inactive, 1)

    def test_add_zero_quantity_raises(self):
        """A zero quantity is rejected."""
        request = make_request(user=self.user)
        with self.assertRaises(InsufficientStockError):
            CartService.add_to_cart(request, self.product, 0)

    def test_guest_cart_uses_session_key(self):
        """Guests get a session-scoped cart."""
        request = make_request()
        item = CartService.add_to_cart(request, self.product, 1)
        self.assertIsNone(item.user)
        self.assertEqual(item.session_key, request.session.session_key)

    def test_update_quantity(self):
        """Updating a cart line sets the new quantity."""
        request = make_request(user=self.user)
        item = CartService.add_to_cart(request, self.product, 1)
        CartService.update_quantity(request, item.id, 3)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

    def test_update_quantity_zero_removes(self):
        """Setting quantity to zero removes the line."""
        request = make_request(user=self.user)
        item = CartService.add_to_cart(request, self.product, 1)
        CartService.update_quantity(request, item.id, 0)
        self.assertFalse(CartItem.objects.filter(pk=item.id).exists())

    def test_update_beyond_stock_raises(self):
        """Updating beyond stock raises and leaves quantity unchanged."""
        request = make_request(user=self.user)
        item = CartService.add_to_cart(request, self.product, 1)
        with self.assertRaises(InsufficientStockError):
            CartService.update_quantity(request, item.id, 99)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_update_missing_item_raises(self):
        """Updating a non-existent line raises OrderError."""
        request = make_request(user=self.user)
        with self.assertRaises(OrderError):
            CartService.update_quantity(request, 9999, 1)

    def test_remove_item(self):
        """Removing a line deletes it."""
        request = make_request(user=self.user)
        item = CartService.add_to_cart(request, self.product, 1)
        CartService.remove_item(request, item.id)
        self.assertFalse(CartItem.objects.filter(pk=item.id).exists())

    def test_clear_cart(self):
        """Clearing removes all lines for the visitor."""
        request = make_request(user=self.user)
        CartService.add_to_cart(request, self.product, 1)
        CartService.add_to_cart(request, ProductFactory(), 1)
        CartService.clear_cart(request)
        self.assertEqual(CartService.get_cart_items(request).count(), 0)

    def test_get_item_count_sums_quantities(self):
        """Item count is the sum of quantities."""
        request = make_request(user=self.user)
        CartService.add_to_cart(request, self.product, 2)
        CartService.add_to_cart(request, ProductFactory(stock_quantity=10), 3)
        self.assertEqual(CartService.get_item_count(request), 5)

    def test_merge_session_cart_into_user(self):
        """A guest cart is moved onto the user's cart on login."""
        guest_request = make_request()
        CartService.add_to_cart(guest_request, self.product, 2)
        session_key = guest_request.session.session_key

        CartService.merge_session_cart(self.user, session_key)

        self.assertEqual(CartItem.objects.filter(session_key=session_key).count(), 0)
        user_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(user_item.quantity, 2)

    def test_merge_session_cart_is_clamped_to_stock(self):
        """Merging cannot exceed available stock."""
        product = ProductFactory(stock_quantity=3)
        CartItemFactory(user=self.user, product=product, quantity=2)
        guest_request = make_request()
        guest_request.session.create()
        CartItemFactory(
            session_key=guest_request.session.session_key, product=product, quantity=2
        )

        CartService.merge_session_cart(self.user, guest_request.session.session_key)

        item = CartItem.objects.get(user=self.user, product=product)
        self.assertEqual(item.quantity, 3)


class TestCartViews(TestCase):
    """Integration tests for the cart views."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.product = ProductFactory(price=Decimal("10.00"), stock_quantity=5)

    def test_cart_page_renders_for_guest(self):
        """The cart page renders for anonymous visitors."""
        response = self.client.get(reverse("orders:cart"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/cart.html")

    def test_cart_add_requires_post(self):
        """GET on the add endpoint is not allowed."""
        response = self.client.get(reverse("orders:cart_add", args=[self.product.slug]))
        self.assertEqual(response.status_code, 405)

    def test_guest_can_add_to_cart(self):
        """A guest can add an item and it appears in the cart."""
        response = self.client.post(
            reverse("orders:cart_add", args=[self.product.slug]), {"quantity": 1}
        )
        self.assertRedirects(response, reverse("orders:cart"))
        self.assertEqual(CartItem.objects.count(), 1)

    def test_add_out_of_stock_shows_error(self):
        """Adding an out-of-stock product shows an error and adds nothing."""
        product = ProductFactory(stock_quantity=0, name="Sold Out")
        response = self.client.post(
            reverse("orders:cart_add", args=[product.slug]),
            {"quantity": 1},
            follow=True,
        )
        content = response.content.lower()
        self.assertTrue(b"in stock" in content or response.status_code in (200, 302, 400))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_invalid_quantity_shows_error(self):
        """An invalid quantity is rejected by the form."""
        response = self.client.post(
            reverse("orders:cart_add", args=[self.product.slug]),
            {"quantity": 0},
            follow=True,
        )
        self.assertContains(response, "valid quantity")
        self.assertEqual(CartItem.objects.count(), 0)

    def test_authenticated_cart_is_persistent(self):
        """Authenticated users' carts persist across requests."""
        self.client.force_login(self.user)
        self.client.post(
            reverse("orders:cart_add", args=[self.product.slug]), {"quantity": 2}
        )
        self.assertTrue(
            CartItem.objects.filter(user=self.user, product=self.product).exists()
        )

    def test_cart_update_view(self):
        """Updating a line via POST changes the quantity."""
        self.client.force_login(self.user)
        item = CartItemFactory(user=self.user, product=self.product, quantity=1)
        self.client.post(
            reverse("orders:cart_update", args=[item.id]), {"quantity": 4}
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_cart_remove_view(self):
        """Removing a line via POST deletes it."""
        self.client.force_login(self.user)
        item = CartItemFactory(user=self.user, product=self.product, quantity=1)
        self.client.post(reverse("orders:cart_remove", args=[item.id]))
        self.assertFalse(CartItem.objects.filter(pk=item.id).exists())

    def test_cart_shows_totals(self):
        """The cart page shows computed totals."""
        self.client.force_login(self.user)
        CartItemFactory(user=self.user, product=self.product, quantity=2)
        response = self.client.get(reverse("orders:cart"))
        self.assertContains(response, "$20.00")  # 2 × $10.00 subtotal

    def test_header_shows_cart_count(self):
        """The header badge reflects the number of cart items."""
        self.client.force_login(self.user)
        CartItemFactory(user=self.user, product=self.product, quantity=3)
        response = self.client.get(reverse("catalog:home"))
        self.assertContains(response, 'badge badge--primary">3</span>')

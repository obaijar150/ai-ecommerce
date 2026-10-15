"""
Tests for checkout: totals, server-side price/stock validation, atomic order
creation, and duplicate-request (idempotency) handling.
"""

from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import ProductInventory
from apps.orders.exceptions import CartValidationError, EmptyCartError
from apps.orders.models import CartItem, Order, OrderItem
from apps.orders.services import CartService, OrderService

from .factories import (
    AddressFactory,
    CartItemFactory,
    ProductFactory,
    UserFactory,
)
from .test_cart import make_request


class TestOrderTotals(TestCase):
    """Tests for OrderService.calculate_totals."""

    def test_totals_include_shipping_and_tax(self):
        """A subtotal below the threshold incurs flat shipping plus tax."""
        product = ProductFactory(price=Decimal("10.00"))
        item = CartItemFactory(product=product, quantity=2)
        totals = OrderService.calculate_totals([item])
        self.assertEqual(totals["subtotal"], Decimal("20.00"))
        self.assertEqual(totals["shipping_cost"], Decimal("5.99"))
        self.assertEqual(totals["tax"], Decimal("1.60"))
        self.assertEqual(totals["total"], Decimal("27.59"))

    def test_totals_free_shipping_over_threshold(self):
        """Shipping is free at or above the free-shipping threshold."""
        product = ProductFactory(price=Decimal("30.00"))
        item = CartItemFactory(product=product, quantity=2)
        totals = OrderService.calculate_totals([item])
        self.assertEqual(totals["shipping_cost"], Decimal("0.00"))
        self.assertEqual(totals["total"], Decimal("64.80"))

    def test_totals_use_sale_price(self):
        """The effective (sale) price is used for totals."""
        product = ProductFactory(price=Decimal("20.00"), sale_price=Decimal("10.00"))
        item = CartItemFactory(product=product, quantity=3)
        totals = OrderService.calculate_totals([item])
        self.assertEqual(totals["subtotal"], Decimal("30.00"))


class TestCreateOrder(TestCase):
    """Tests for OrderService.create_order."""

    def setUp(self):
        self.user = UserFactory()
        self.address = AddressFactory(user=self.user)
        self.product = ProductFactory(price=Decimal("10.00"), stock_quantity=10)

    def _cart(self):
        request = make_request(user=self.user)
        CartService.add_to_cart(request, self.product, 2)
        return CartService.get_cart_items(request)

    def test_create_order_success(self):
        """Creating an order snapshots items and computes totals."""
        order, created = OrderService.create_order(
            user=self.user, cart_items=self._cart(), shipping_address=self.address
        )
        self.assertTrue(created)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.subtotal, Decimal("20.00"))
        self.assertEqual(order.total, Decimal("27.59"))
        self.assertEqual(order.items.count(), 1)

    def test_create_order_snapshots_product_name_and_sku(self):
        """Order items keep a copy of the product name and SKU."""
        order, _ = OrderService.create_order(
            user=self.user, cart_items=self._cart(), shipping_address=self.address
        )
        item = order.items.first()
        self.assertEqual(item.product_name, self.product.name)
        self.assertEqual(item.product_sku, self.product.sku)

    def test_create_order_decrements_stock(self):
        """Stock is reduced by the ordered quantity."""
        OrderService.create_order(
            user=self.user, cart_items=self._cart(), shipping_address=self.address
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_create_order_decrements_inventory(self):
        """Linked inventory records are reduced too."""
        inventory = ProductInventory.objects.create(
            product=self.product, quantity=10
        )
        OrderService.create_order(
            user=self.user, cart_items=self._cart(), shipping_address=self.address
        )
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 8)

    def test_create_order_clears_cart(self):
        """The cart is emptied after a successful order."""
        cart = self._cart()
        OrderService.create_order(
            user=self.user, cart_items=cart, shipping_address=self.address
        )
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)

    def test_create_order_records_status_history(self):
        """An initial status-history entry is written."""
        order, _ = OrderService.create_order(
            user=self.user, cart_items=self._cart(), shipping_address=self.address
        )
        self.assertEqual(order.status_history.count(), 1)
        self.assertEqual(order.status_history.first().status, Order.Status.PENDING)

    def test_empty_cart_raises(self):
        """An empty cart cannot be checked out."""
        request = make_request(user=self.user)
        with self.assertRaises(EmptyCartError):
            OrderService.create_order(
                user=self.user,
                cart_items=CartService.get_cart_items(request),
                shipping_address=self.address,
            )

    def test_insufficient_stock_raises_and_creates_nothing(self):
        """Insufficient stock aborts the order and leaves stock untouched."""
        cart = self._cart()
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])
        with self.assertRaises(CartValidationError):
            OrderService.create_order(
                user=self.user, cart_items=cart, shipping_address=self.address
            )
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

    def test_inactive_product_raises(self):
        """A deactivated product aborts checkout."""
        cart = self._cart()
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        with self.assertRaises(CartValidationError):
            OrderService.create_order(
                user=self.user, cart_items=cart, shipping_address=self.address
            )
        self.assertEqual(Order.objects.count(), 0)

    def test_invalid_price_raises(self):
        """A non-positive price aborts checkout."""
        self.product.price = Decimal("0.00")
        self.product.sale_price = None
        self.product.save(update_fields=["price", "sale_price"])
        with self.assertRaises(CartValidationError):
            OrderService.create_order(
                user=self.user, cart_items=self._cart(), shipping_address=self.address
            )

    def test_server_recomputes_price(self):
        """The order uses the current DB price, ignoring any stale value."""
        cart = self._cart()
        self.product.price = Decimal("12.00")
        self.product.save(update_fields=["price"])
        order, _ = OrderService.create_order(
            user=self.user, cart_items=cart, shipping_address=self.address
        )
        self.assertEqual(order.subtotal, Decimal("24.00"))

    def test_duplicate_idempotency_key_returns_same_order(self):
        """A repeated submission with the same key does not double-order."""
        cart = self._cart()
        order1, created1 = OrderService.create_order(
            user=self.user,
            cart_items=cart,
            shipping_address=self.address,
            idempotency_key="abc123",
        )
        # Second call: cart is now empty, but the key short-circuits first.
        order2, created2 = OrderService.create_order(
            user=self.user,
            cart_items=CartService.get_cart_items(make_request(user=self.user)),
            shipping_address=self.address,
            idempotency_key="abc123",
        )
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(order1.pk, order2.pk)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)  # decremented only once

    def test_totals_cannot_be_oversold_across_orders(self):
        """Two sequential orders cannot exceed available stock."""
        self.product.stock_quantity = 3
        self.product.save(update_fields=["stock_quantity"])

        request = make_request(user=self.user)
        CartService.add_to_cart(request, self.product, 3)
        OrderService.create_order(
            user=self.user,
            cart_items=CartService.get_cart_items(request),
            shipping_address=self.address,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)

        # A second attempt must fail because stock is exhausted.
        request2 = make_request(user=self.user)
        # Adding is blocked by the cart service, simulating an honest client.
        from apps.orders.exceptions import InsufficientStockError

        with self.assertRaises(InsufficientStockError):
            CartService.add_to_cart(request2, self.product, 1)

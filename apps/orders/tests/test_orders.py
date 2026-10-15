"""
Tests for order lifecycle: status transitions, cancellation, stock restoration,
and order history/detail access rules.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.orders.exceptions import OrderError
from apps.orders.models import Order
from apps.orders.services import OrderService

from .factories import (
    AddressFactory,
    OrderFactory,
    OrderItemFactory,
    ProductFactory,
    UserFactory,
)


class TestOrderTransitions(TestCase):
    """Tests for OrderService.transition."""

    def setUp(self):
        self.order = OrderFactory(status=Order.Status.PENDING)

    def test_pending_can_be_cancelled(self):
        """A pending order can be cancelled."""
        OrderService.transition(self.order, Order.Status.CANCELLED, "test")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_transition_records_history(self):
        """Each transition appends to the status history."""
        OrderService.transition(self.order, Order.Status.CANCELLED, "why not")
        self.assertEqual(self.order.status_history.count(), 1)
        self.assertEqual(self.order.status_history.first().notes, "why not")

    def test_cannot_jump_pending_to_delivered(self):
        """Invalid transitions are rejected."""
        with self.assertRaises(OrderError):
            OrderService.transition(self.order, Order.Status.DELIVERED)

    def test_transition_cannot_set_paid(self):
        """Status changes cannot mark an order paid directly."""
        with self.assertRaises(OrderError):
            OrderService.transition(self.order, Order.Status.PAID)


class TestCancelOrder(TestCase):
    """Tests for cancelling orders and restoring stock."""

    def setUp(self):
        self.user = UserFactory()
        self.product = ProductFactory(stock_quantity=10)

    def _order_with_item(self, quantity=2):
        order = OrderFactory(user=self.user, status=Order.Status.PENDING)
        OrderItemFactory(
            order=order,
            product=self.product,
            quantity=quantity,
            unit_price=self.product.current_price,
            total_price=self.product.current_price * quantity,
        )
        return order

    def test_cancel_pending_restores_stock(self):
        """Cancelling a pending order returns items to stock."""
        self.product.stock_quantity = 8
        self.product.save(update_fields=["stock_quantity"])
        order = self._order_with_item(quantity=2)

        OrderService.cancel_order(order, changed_by=self.user)

        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_cancel_paid_marks_refunded_and_restores_stock(self):
        """Cancelling a paid order refunds it and restores stock."""
        order = self._order_with_item(quantity=3)
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])

        OrderService.cancel_order(order, changed_by=self.user)

        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(self.product.stock_quantity, 13)

    def test_cancel_delivered_order_raises(self):
        """Delivered orders cannot be cancelled."""
        order = OrderFactory(user=self.user, status=Order.Status.DELIVERED)
        with self.assertRaises(OrderError):
            OrderService.cancel_order(order)


class TestOrderAccess(TestCase):
    """Order history and detail pages enforce ownership."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.other = UserFactory()
        self.order = OrderFactory(user=self.user)

    def test_order_list_requires_login(self):
        """Anonymous users are redirected to login."""
        response = self.client.get(reverse("orders:order_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_order_list_shows_own_orders(self):
        """Users see their own orders."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("orders:order_list"))
        self.assertContains(response, self.order.short_id)

    def test_order_detail_private(self):
        """Users cannot view another user's order."""
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("orders:order_detail", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_order_detail_own(self):
        """Users can view their own order detail."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("orders:order_detail", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/order_detail.html")

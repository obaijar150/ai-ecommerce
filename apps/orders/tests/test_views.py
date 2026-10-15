"""
End-to-end tests for the checkout and order views.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Address
from apps.catalog.models import Product
from apps.orders.models import CartItem, Order, Payment
from apps.orders.payments import TOKEN_FAILURE, TOKEN_SUCCESS

from .factories import (
    AddressFactory,
    CartItemFactory,
    OrderFactory,
    OrderItemFactory,
    ProductFactory,
    UserFactory,
)


class TestCheckoutFlow(TestCase):
    """Full checkout flows through the views."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.product = ProductFactory(price=Decimal("10.00"), stock_quantity=10)
        self.client.force_login(self.user)

    def _checkout_data(self, **overrides):
        data = {
            "label": "Home",
            "street": "1 Main St",
            "city": "Town",
            "state": "TS",
            "postal_code": "12345",
            "country": "United States",
            "payment_method": Order.PaymentMethod.MOCK_CARD,
            "payment_token": TOKEN_SUCCESS,
        }
        data.update(overrides)
        return data

    def test_checkout_requires_login(self):
        """Anonymous users are redirected to login."""
        self.client.logout()
        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_checkout_empty_cart_redirects(self):
        """An empty cart redirects back to the cart page."""
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("orders:cart"))

    def test_checkout_get_renders_form(self):
        """The checkout page renders with a form."""
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/checkout.html")
        self.assertContains(response, "Order Summary")

    def test_successful_checkout_creates_paid_order(self):
        """A valid checkout creates a paid order and clears the cart."""
        CartItemFactory(user=self.user, product=self.product, quantity=2)
        response = self.client.post(
            reverse("orders:checkout"), self._checkout_data()
        )
        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            response, reverse("orders:order_confirmation", args=[order.pk])
        )
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, Decimal("27.59"))
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_checkout_creates_new_address(self):
        """Providing new-address fields creates an Address."""
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)

    def test_checkout_uses_saved_address(self):
        """A saved address can be selected instead of entering a new one."""
        address = AddressFactory(user=self.user)
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        response = self.client.post(
            reverse("orders:checkout"),
            self._checkout_data(address=address.pk, street="", city="", state="", postal_code=""),
        )
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.shipping_address_id, address.pk)
        self.assertEqual(response.status_code, 302)

    def test_failed_payment_keeps_order_pending(self):
        """A failed payment redirects to the order and leaves it pending."""
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        response = self.client.post(
            reverse("orders:checkout"),
            self._checkout_data(payment_token=TOKEN_FAILURE),
        )
        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            response, reverse("orders:order_detail", args=[order.pk])
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payments.count(), 1)
        self.assertEqual(order.payments.first().status, Payment.Status.FAILED)

    def test_insufficient_stock_blocks_checkout(self):
        """Insufficient stock redirects to the cart and creates no order."""
        item = CartItemFactory(user=self.user, product=self.product, quantity=2)
        # Stock drops below the requested quantity after the item was added.
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        response = self.client.post(
            reverse("orders:checkout"), self._checkout_data(), follow=True
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(response, "in stock")

    def test_duplicate_submission_creates_one_order(self):
        """Submitting checkout twice creates a single order."""
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        self.assertEqual(Order.objects.count(), 1)

    def test_cash_on_delivery_leaves_order_unpaid(self):
        """Cash-on-delivery orders are placed without being marked paid."""
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        response = self.client.post(
            reverse("orders:checkout"),
            self._checkout_data(
                payment_method=Order.PaymentMethod.CASH_ON_DELIVERY,
                payment_token="",
            ),
        )
        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            response, reverse("orders:order_confirmation", args=[order.pk])
        )
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payments.count(), 0)

    def test_checkout_rejects_card_number(self):
        """A card-number token is rejected before any order is created."""
        CartItemFactory(user=self.user, product=self.product, quantity=1)
        self.client.post(
            reverse("orders:checkout"),
            self._checkout_data(payment_token="4111111111111111"),
        )
        self.assertEqual(Order.objects.count(), 0)


class TestPaymentRetry(TestCase):
    """Tests for retrying payment on a pending order."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.order = OrderFactory(user=self.user, status=Order.Status.PENDING)
        self.client.force_login(self.user)

    def test_retry_payment_succeeds(self):
        """Retrying with a success token marks the order paid."""
        response = self.client.post(
            reverse("orders:order_pay", args=[self.order.pk]),
            {"payment_token": TOKEN_SUCCESS},
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertRedirects(
            response, reverse("orders:order_confirmation", args=[self.order.pk])
        )

    def test_retry_payment_failure_keeps_pending(self):
        """Retrying with a failure token keeps the order pending."""
        self.client.post(
            reverse("orders:order_pay", args=[self.order.pk]),
            {"payment_token": TOKEN_FAILURE},
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)


class TestOrderCancelView(TestCase):
    """Tests for the cancel-order view."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.product = ProductFactory(stock_quantity=5)
        self.order = OrderFactory(user=self.user, status=Order.Status.PENDING)
        OrderItemFactory(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("10.00"),
            total_price=Decimal("20.00"),
        )
        self.client.force_login(self.user)

    def test_cancel_order_view(self):
        """Posting to cancel restores stock and sets the order cancelled."""
        response = self.client.post(
            reverse("orders:order_cancel", args=[self.order.pk])
        )
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertRedirects(
            response, reverse("orders:order_detail", args=[self.order.pk])
        )


class TestOrderConfirmation(TestCase):
    """Tests for the confirmation page."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.order = OrderFactory(user=self.user, status=Order.Status.PAID)

    def test_confirmation_requires_login(self):
        """Anonymous users cannot view a confirmation page."""
        response = self.client.get(
            reverse("orders:order_confirmation", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_confirmation_renders(self):
        """The confirmation page renders for the owner."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("orders:order_confirmation", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/order_confirmation.html")

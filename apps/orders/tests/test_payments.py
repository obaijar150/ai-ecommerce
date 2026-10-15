"""
Tests for the payment abstraction: mock provider, verified confirmation,
idempotency, and the guarantee that no card data is ever stored.
"""

from decimal import Decimal

from django.test import TestCase, override_settings

from apps.orders.forms import CheckoutForm
from apps.orders.models import Order, Payment
from apps.orders.payments import (
    TOKEN_FAILURE,
    TOKEN_SUCCESS,
    MockPaymentProvider,
    get_payment_provider,
)
from apps.orders.services import PaymentService

from .factories import OrderFactory


class TestMockProvider(TestCase):
    """Tests for the mock payment provider."""

    def setUp(self):
        self.provider = MockPaymentProvider()
        self.order = OrderFactory()

    def test_success_token(self):
        """The success token returns a successful result with a reference."""
        result = self.provider.charge(
            order=self.order, amount=Decimal("10.00"), token=TOKEN_SUCCESS
        )
        self.assertTrue(result.success)
        self.assertTrue(result.transaction_id.startswith("mock_"))

    def test_failure_token(self):
        """The failure token returns an unsuccessful result."""
        result = self.provider.charge(
            order=self.order, amount=Decimal("10.00"), token=TOKEN_FAILURE
        )
        self.assertFalse(result.success)

    def test_invalid_amount_fails(self):
        """A non-positive amount is rejected."""
        result = self.provider.charge(order=self.order, amount=Decimal("0.00"))
        self.assertFalse(result.success)

    def test_unknown_provider_raises(self):
        """Requesting an unknown provider raises ValueError."""
        with self.assertRaises(ValueError):
            get_payment_provider("does-not-exist")

    @override_settings(MOCK_PAYMENT_FAILURE_RATE=1.0)
    def test_random_failure_rate(self):
        """A 100% failure rate fails unknown tokens."""
        result = self.provider.charge(
            order=self.order, amount=Decimal("10.00"), token="tok_whatever"
        )
        self.assertFalse(result.success)


class TestPaymentService(TestCase):
    """Tests for PaymentService.process_payment."""

    def setUp(self):
        self.order = OrderFactory(total=Decimal("27.59"))

    def test_successful_payment_marks_order_paid(self):
        """A confirmed payment sets status PAID and records paid_at."""
        payment = PaymentService.process_payment(self.order, token=TOKEN_SUCCESS)
        self.order.refresh_from_db()
        self.assertTrue(payment.succeeded)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertIsNotNone(self.order.paid_at)

    def test_successful_payment_records_history(self):
        """A confirmed payment adds a status-history entry."""
        PaymentService.process_payment(self.order, token=TOKEN_SUCCESS)
        self.assertTrue(
            self.order.status_history.filter(status=Order.Status.PAID).exists()
        )

    def test_failed_payment_does_not_mark_paid(self):
        """A declined payment leaves the order pending and un-paid."""
        payment = PaymentService.process_payment(self.order, token=TOKEN_FAILURE)
        self.order.refresh_from_db()
        self.assertFalse(payment.succeeded)
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertIsNone(self.order.paid_at)

    def test_failed_payment_records_reason(self):
        """A declined payment stores a human-readable reason."""
        payment = PaymentService.process_payment(self.order, token=TOKEN_FAILURE)
        self.assertTrue(payment.failure_reason)

    def test_payment_is_idempotent(self):
        """Paying an already-paid order does not create a second charge."""
        first = PaymentService.process_payment(self.order, token=TOKEN_SUCCESS)
        second = PaymentService.process_payment(self.order, token=TOKEN_SUCCESS)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)

    def test_only_confirmed_success_marks_paid(self):
        """The order is never marked paid unless the provider confirms it."""
        PaymentService.process_payment(self.order, token=TOKEN_FAILURE)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)
        self.assertFalse(
            self.order.status_history.filter(status=Order.Status.PAID).exists()
        )


class TestNoSensitiveDataStored(TestCase):
    """Ensure the payment layer never stores card data."""

    def test_payment_model_has_no_card_fields(self):
        """The Payment model exposes no card-number/CVV fields."""
        field_names = {f.name for f in Payment._meta.get_fields()}
        forbidden = {"card_number", "cvv", "cvc", "card_cvv", "pan", "security_code"}
        self.assertFalse(forbidden & field_names)

    def test_raw_response_never_contains_card_data(self):
        """The persisted raw response only contains non-sensitive metadata."""
        order = OrderFactory(total=Decimal("27.59"))
        payment = PaymentService.process_payment(order, token=TOKEN_SUCCESS)
        self.assertNotIn("card_number", payment.raw_response)
        self.assertNotIn("cvv", payment.raw_response)


class TestCheckoutFormRejectsCardNumbers(TestCase):
    """The checkout form refuses anything resembling a card number."""

    def test_card_number_token_is_rejected(self):
        """A 16-digit token is rejected as a card number."""
        form = CheckoutForm(
            data={
                "street": "1 Main St",
                "city": "Town",
                "state": "TS",
                "postal_code": "12345",
                "country": "United States",
                "payment_method": "mock_card",
                "payment_token": "4111111111111111",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("payment_token", form.errors)

    def test_mock_token_is_accepted(self):
        """A legitimate mock token passes form validation."""
        form = CheckoutForm(
            data={
                "street": "1 Main St",
                "city": "Town",
                "state": "TS",
                "postal_code": "12345",
                "country": "United States",
                "payment_method": "mock_card",
                "payment_token": TOKEN_SUCCESS,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

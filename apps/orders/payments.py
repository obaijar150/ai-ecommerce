"""
Payment provider abstraction.

The platform ships **only** with free/mock providers. A provider is a small
class that receives an order and returns a :class:`PaymentResult`.

Security rules enforced by design:

* No provider is ever handed a card number or CVV. Providers only receive an
  opaque ``token`` (a stand-in for a payment-method token) and the amount.
* An order may only be marked paid after a provider explicitly confirms
  success (:class:`PaymentResult.success` is ``True``).

To add a real (free) provider later, implement :class:`PaymentProvider` and
register it in :data:`PROVIDERS`. Paid services must not be made a hard
requirement (see project rules).
"""

from __future__ import annotations

import secrets
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from django.conf import settings


# Token values understood by the mock provider. They let developers and tests
# simulate outcomes without any real card data.
TOKEN_SUCCESS = "tok_success"
TOKEN_FAILURE = "tok_failure"


@dataclass
class PaymentResult:
    """Outcome of a payment attempt.

    Attributes:
        success: Whether the provider verified the payment succeeded.
        transaction_id: Opaque provider reference (never card data).
        message: Human-readable status/error message.
        raw: Non-sensitive provider metadata to persist for auditing.
    """

    success: bool
    transaction_id: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)


class PaymentProvider(ABC):
    """Base class for payment providers."""

    name: str = "base"
    label: str = "Payment Provider"

    @abstractmethod
    def charge(self, *, order, amount, token: str | None = None) -> PaymentResult:
        """Attempt to charge ``amount`` for ``order``.

        Args:
            order: The :class:`~apps.orders.models.Order` being paid.
            amount: A :class:`~decimal.Decimal` total to charge.
            token: Opaque payment-method token. Never a card number.

        Returns:
            A :class:`PaymentResult`.
        """
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    """A local-development provider that simulates payment outcomes.

    Outcomes:

    * ``token == "tok_failure"`` → always fails.
    * ``token == "tok_success"`` (or empty) → always succeeds.
    * otherwise → succeeds unless ``MOCK_PAYMENT_FAILURE_RATE`` says otherwise.
    """

    name = "mock"
    label = "Mock Card (development only)"

    def charge(self, *, order, amount, token: str | None = None) -> PaymentResult:
        if amount is None or amount <= 0:
            return PaymentResult(
                success=False,
                message="Invalid payment amount.",
                raw={"reason": "invalid_amount"},
            )

        if token == TOKEN_FAILURE:
            return PaymentResult(
                success=False,
                message="Your card was declined (mock).",
                raw={"reason": "declined", "token": token},
            )

        if token not in (TOKEN_SUCCESS, "", None):
            # Unknown token: fall back to the configured random failure rate.
            failure_rate = float(getattr(settings, "MOCK_PAYMENT_FAILURE_RATE", 0.0))
            if failure_rate > 0 and random.random() < failure_rate:
                return PaymentResult(
                    success=False,
                    message="The mock gateway was unavailable. Please try again.",
                    raw={"reason": "gateway_unavailable"},
                )

        transaction_id = f"mock_{secrets.token_hex(8)}"
        return PaymentResult(
            success=True,
            transaction_id=transaction_id,
            message="Payment approved (mock).",
            raw={"token": token or TOKEN_SUCCESS},
        )


# Registry of available providers. Keep this list to free/mock providers only.
PROVIDERS: dict[str, type[PaymentProvider]] = {
    MockPaymentProvider.name: MockPaymentProvider,
}


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    """Return a payment provider instance.

    Args:
        name: Provider key; defaults to ``settings.PAYMENT_PROVIDER``.

    Returns:
        A :class:`PaymentProvider` instance.

    Raises:
        ValueError: If the provider is unknown.
    """
    key = name or getattr(settings, "PAYMENT_PROVIDER", MockPaymentProvider.name)
    provider_cls = PROVIDERS.get(key)
    if provider_cls is None:
        raise ValueError(f"Unknown payment provider: {key!r}")
    return provider_cls()


def get_payment_method_choices() -> list[tuple[str, str]]:
    """Return the payment method choices for checkout forms."""
    from .models import Order

    return list(Order.PaymentMethod.choices)

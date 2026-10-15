"""
Domain exceptions for the orders app.

These carry user-facing, safe messages so views can surface clear errors
without leaking internal details.
"""


class OrderError(Exception):
    """Base class for all order/cart domain errors."""

    default_message = "Something went wrong while processing your order."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class EmptyCartError(OrderError):
    """Raised when checkout is attempted with no items."""

    default_message = "Your cart is empty."


class ProductUnavailableError(OrderError):
    """Raised when a cart product is inactive or no longer purchasable."""

    default_message = "One or more products are no longer available."


class InvalidPriceError(OrderError):
    """Raised when a product has an invalid (non-positive) price."""

    default_message = "One or more products have an invalid price."


class InsufficientStockError(OrderError):
    """Raised when requested quantity exceeds available stock."""

    default_message = "One or more items do not have enough stock."

    def __init__(self, message: str | None = None, shortages: list | None = None):
        super().__init__(message)
        self.shortages = shortages or []


class CartValidationError(OrderError):
    """Raised when the cart fails server-side validation.

    Attributes:
        errors: Human-readable list of problems found in the cart.
    """

    default_message = "Some items in your cart could not be ordered."

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(" ".join(errors))


class PaymentError(OrderError):
    """Raised when a payment cannot be completed."""

    default_message = "Payment could not be processed."

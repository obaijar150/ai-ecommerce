"""
Orders models: CartItem, Order, OrderItem, OrderStatusHistory, Payment.

Security note
-------------
The :class:`Payment` model intentionally stores **no** cardholder data. Only a
provider name, an opaque transaction reference, an amount and a status are
persisted. Card numbers and CVV values must never be stored anywhere in this
system.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class CartItem(models.Model):
    """A single line in a shopping cart.

    Carts are persistent for authenticated users (linked by ``user``) and
    session-based for guests (linked by ``session_key``). Exactly one of the
    two must be set.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-added_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user__isnull=False)
                | models.Q(session_key__isnull=False),
                name="cart_item_must_have_user_or_session",
            ),
            models.UniqueConstraint(
                fields=["user", "product"],
                condition=models.Q(user__isnull=False),
                name="unique_cart_item_per_user_product",
            ),
            models.UniqueConstraint(
                fields=["session_key", "product"],
                condition=models.Q(session_key__isnull=False),
                name="unique_cart_item_per_session_product",
            ),
        ]

    @property
    def unit_price(self) -> Decimal:
        """Return the current effective price of the product."""
        return self.product.current_price

    @property
    def line_total(self) -> Decimal:
        """Return ``unit_price * quantity``."""
        return self.product.current_price * self.quantity

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product.name}"


class Order(models.Model):
    """A customer order with status and payment tracking."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        MOCK_CARD = "mock_card", "Mock Card"
        CASH_ON_DELIVERY = "cash_on_delivery", "Cash on Delivery"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        related_name="shipping_orders",
        null=True,
    )
    billing_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        related_name="billing_orders",
        null=True,
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MOCK_CARD,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    # Used to make checkout submissions idempotent (duplicate requests).
    idempotency_key = models.CharField(
        max_length=64, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    @property
    def short_id(self) -> str:
        """First 8 characters of the order id, for display."""
        return str(self.id)[:8]

    @property
    def is_paid(self) -> bool:
        """True when the order has been paid (or moved beyond payment)."""
        return self.status in {
            self.Status.PAID,
            self.Status.SHIPPED,
            self.Status.DELIVERED,
        }

    @property
    def can_be_cancelled(self) -> bool:
        """True when the order can still be cancelled by the customer."""
        return self.status in {self.Status.PENDING, self.Status.PAID}

    @property
    def latest_payment(self):
        """Return the most recent payment attempt, if any."""
        return self.payments.order_by("-created_at").first()

    def __str__(self) -> str:
        return f"Order #{self.short_id} by {self.user.username}"


class OrderItem(models.Model):
    """A line item within an order.

    Product name, SKU and unit price are snapshotted at purchase time so the
    order remains accurate even if the product is later edited or deleted.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    product_name = models.CharField(max_length=200, blank=True)
    product_sku = models.CharField(max_length=50, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    @property
    def display_name(self) -> str:
        """Return the snapshotted name, falling back to the live product."""
        return self.product_name or (self.product.name if self.product else "Product")

    def __str__(self) -> str:
        return f"{self.quantity}× {self.display_name}"


class OrderStatusHistory(models.Model):
    """Audit trail of order status changes."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_history"
    )
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "order status histories"

    def __str__(self) -> str:
        return f"{self.order.short_id} → {self.status}"


class Payment(models.Model):
    """A payment attempt against an order.

    Only non-sensitive metadata is stored: the provider, an opaque transaction
    reference, the amount and the result. **Never** store card numbers, CVV
    values or other cardholder data here.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments"
    )
    provider = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    failure_reason = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def succeeded(self) -> bool:
        return self.status == self.Status.SUCCEEDED

    def mark_succeeded(self, transaction_id: str, raw: dict | None = None) -> None:
        """Record a verified successful payment."""
        self.status = self.Status.SUCCEEDED
        self.transaction_id = transaction_id
        self.raw_response = raw or {}
        self.confirmed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "transaction_id",
                "raw_response",
                "confirmed_at",
                "updated_at",
            ]
        )

    def mark_failed(self, reason: str, raw: dict | None = None) -> None:
        """Record a failed payment attempt."""
        self.status = self.Status.FAILED
        self.failure_reason = reason[:255]
        self.raw_response = raw or {}
        self.save(
            update_fields=["status", "failure_reason", "raw_response", "updated_at"]
        )

    def __str__(self) -> str:
        return f"{self.provider} {self.status} ({self.amount})"

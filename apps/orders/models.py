"""
Orders models: CartItem, Order, OrderItem, OrderStatusHistory.
"""

from django.conf import settings
from django.db import models


class CartItem(models.Model):
    """Shopping cart item — session-based for guests, user-linked for auth users."""

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

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name="cart_item_must_have_user_or_session",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product.name}"


class Order(models.Model):
    """Customer order with status tracking."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

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
    payment_method = models.CharField(max_length=50, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.id[:8]} by {self.user.username}"


class OrderItem(models.Model):
    """Individual items within an order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product.name if self.product else 'N/A'}"


class OrderStatusHistory(models.Model):
    """Audit trail of order status changes."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_history"
    )
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.id[:8]} → {self.status}"

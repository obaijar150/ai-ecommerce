"""
Orders services: cart management, order creation, pricing calculations.
"""

from decimal import Decimal
from typing import Optional

from django.db import transaction

from apps.catalog.models import Product

from .models import CartItem, Order, OrderItem, OrderStatusHistory


class CartService:
    """Service for managing shopping cart operations."""

    @staticmethod
    def get_cart_items(user=None, session_key: Optional[str] = None):
        """Retrieve cart items for authenticated user or guest session."""
        if user and user.is_authenticated:
            return CartItem.objects.filter(user=user).select_related("product")
        elif session_key:
            return CartItem.objects.filter(session_key=session_key).select_related(
                "product"
            )
        return CartItem.objects.none()

    @staticmethod
    def add_to_cart(
        product: Product,
        quantity: int = 1,
        user=None,
        session_key: Optional[str] = None,
    ) -> CartItem:
        """Add a product to cart or update quantity if already present."""
        if user and user.is_authenticated:
            cart_item, created = CartItem.objects.get_or_create(
                user=user, product=product, defaults={"quantity": quantity}
            )
        else:
            cart_item, created = CartItem.objects.get_or_create(
                session_key=session_key,
                product=product,
                defaults={"quantity": quantity},
            )

        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=["quantity"])

        return cart_item

    @staticmethod
    def get_cart_total(user=None, session_key: Optional[str] = None) -> Decimal:
        """Calculate total price of all cart items."""
        items = CartService.get_cart_items(user, session_key)
        return sum(item.product.current_price * item.quantity for item in items)


class OrderService:
    """Service for order creation and management."""

    SHIPPING_THRESHOLD = Decimal("50.00")
    SHIPPING_COST = Decimal("5.99")
    TAX_RATE = Decimal("0.08")

    @staticmethod
    def calculate_totals(cart_items) -> dict:
        """Calculate subtotal, shipping, tax, and total."""
        subtotal = sum(
            item.product.current_price * item.quantity for item in cart_items
        )
        shipping = (
            Decimal("0") if subtotal > OrderService.SHIPPING_THRESHOLD
            else OrderService.SHIPPING_COST
        )
        tax = round(subtotal * OrderService.TAX_RATE, 2)
        total = subtotal + shipping + tax

        return {
            "subtotal": subtotal,
            "shipping_cost": shipping,
            "tax": tax,
            "total": total,
        }

    @staticmethod
    @transaction.atomic
    def create_order(user, cart_items, shipping_address, billing_address) -> Order:
        """Create order from cart items within a database transaction."""
        totals = OrderService.calculate_totals(cart_items)

        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            subtotal=totals["subtotal"],
            shipping_cost=totals["shipping_cost"],
            tax=totals["tax"],
            total=totals["total"],
            shipping_address=shipping_address,
            billing_address=billing_address,
        )

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.current_price,
                total_price=cart_item.product.current_price * cart_item.quantity,
            )

        # Create initial status history entry
        OrderStatusHistory.objects.create(
            order=order, status=Order.Status.PENDING, notes="Order created"
        )

        # Clear the cart
        cart_items.delete()

        return order

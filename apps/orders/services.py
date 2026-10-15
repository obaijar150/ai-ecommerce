"""
Orders services: cart management, order creation, pricing and payments.

All business logic lives here so views stay thin. Stock is validated and
decremented inside a database transaction to prevent overselling.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalog.models import Product

from .exceptions import (
    CartValidationError,
    EmptyCartError,
    InsufficientStockError,
    OrderError,
)
from .models import CartItem, Order, OrderItem, OrderStatusHistory, Payment
from .payments import get_payment_provider

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value) -> Decimal:
    """Quantize a value to two decimal places (bankers-safe rounding)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


class CartService:
    """Manage shopping cart operations for users and guests."""

    @staticmethod
    def _session_key(request) -> str | None:
        """Return the request's session key, creating a session if needed.

        The key is also stored in the session data so a guest cart can be
        merged onto a user account after login (session *data* survives the
        session-key cycling that happens on login).
        """
        if not request.session.session_key:
            request.session.create()
        request.session["guest_cart_key"] = request.session.session_key
        return request.session.session_key

    @staticmethod
    def get_cart_items(request):
        """Return the cart queryset for the current visitor.

        Never creates a session (safe to call from a context processor).
        """
        if request.user.is_authenticated:
            return CartItem.objects.filter(user=request.user).select_related(
                "product", "product__brand"
            )
        key = request.session.session_key
        if not key:
            return CartItem.objects.none()
        return CartItem.objects.filter(session_key=key).select_related(
            "product", "product__brand"
        )

    @staticmethod
    def get_item_count(request) -> int:
        """Return the total quantity of items in the visitor's cart."""
        return CartService.get_cart_items(request).aggregate(total=Sum("quantity"))[
            "total"
        ] or 0

    @staticmethod
    def _validate_addition(product: Product, new_quantity: int) -> None:
        """Ensure a product may be added to the cart in the given quantity."""
        if new_quantity <= 0:
            raise InsufficientStockError("Quantity must be at least 1.")
        if not product.is_active:
            raise InsufficientStockError(f"'{product.name}' is no longer available.")
        if new_quantity > product.stock_quantity:
            raise InsufficientStockError(
                f"Only {product.stock_quantity} of '{product.name}' are in stock."
            )

    @staticmethod
    @transaction.atomic
    def add_to_cart(request, product: Product, quantity: int = 1) -> CartItem:
        """Add ``quantity`` of ``product`` to the cart (merging duplicates)."""
        quantity = int(quantity)
        if quantity <= 0:
            raise InsufficientStockError("Quantity must be at least 1.")

        if request.user.is_authenticated:
            lookup = {"user": request.user, "product": product}
        else:
            lookup = {
                "session_key": CartService._session_key(request),
                "product": product,
            }

        item = CartItem.objects.select_for_update().filter(**lookup).first()
        new_quantity = (item.quantity if item else 0) + quantity
        CartService._validate_addition(product, new_quantity)

        if item:
            item.quantity = new_quantity
            item.save(update_fields=["quantity", "updated_at"])
            return item
        return CartItem.objects.create(quantity=quantity, **lookup)

    @staticmethod
    @transaction.atomic
    def update_quantity(request, item_id: int, quantity: int) -> None:
        """Set the quantity of a cart line; removes it when quantity is 0."""
        item = CartService.get_cart_items(request).select_for_update().filter(
            pk=item_id
        ).first()
        if item is None:
            raise OrderError("That cart item no longer exists.")

        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
            return

        CartService._validate_addition(item.product, quantity)
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])

    @staticmethod
    def remove_item(request, item_id: int) -> None:
        """Remove a single line from the cart."""
        item = CartService.get_cart_items(request).filter(pk=item_id).first()
        if item is None:
            raise OrderError("That cart item no longer exists.")
        item.delete()

    @staticmethod
    def clear_cart(request) -> None:
        """Remove every line from the visitor's cart."""
        CartService.get_cart_items(request).delete()

    @staticmethod
    @transaction.atomic
    def merge_session_cart(user, session_key: str | None) -> None:
        """Move a guest cart onto a user's account after login.

        Quantities are merged and clamped to available stock so a stale guest
        cart cannot exceed inventory.
        """
        if not session_key:
            return
        guest_items = CartItem.objects.filter(session_key=session_key)
        for item in guest_items:
            existing = CartItem.objects.filter(user=user, product=item.product).first()
            if existing:
                merged = min(
                    existing.quantity + item.quantity, item.product.stock_quantity
                )
                existing.quantity = max(merged, 1)
                existing.save(update_fields=["quantity", "updated_at"])
            else:
                CartItem.objects.create(
                    user=user,
                    product=item.product,
                    quantity=min(item.quantity, item.product.stock_quantity) or 1,
                )
        guest_items.delete()


class OrderService:
    """Create and manage orders."""

    @staticmethod
    def _shipping_for(subtotal: Decimal) -> Decimal:
        """Return the shipping cost for a subtotal."""
        threshold = Decimal(str(getattr(settings, "FREE_SHIPPING_THRESHOLD", "50.00")))
        if subtotal >= threshold:
            return ZERO
        return _money(getattr(settings, "SHIPPING_FLAT_RATE", "5.99"))

    @staticmethod
    def _tax_for(subtotal: Decimal) -> Decimal:
        """Return the sales tax for a subtotal."""
        rate = Decimal(str(getattr(settings, "SALES_TAX_RATE", "0.08")))
        return _money(subtotal * rate)

    @staticmethod
    def calculate_totals(items) -> dict:
        """Calculate subtotal, shipping, tax and total for cart items.

        Uses each product's current effective (sale-aware) price.
        """
        subtotal = sum((item.product.current_price * item.quantity for item in items), ZERO)
        subtotal = _money(subtotal)
        shipping = OrderService._shipping_for(subtotal)
        tax = OrderService._tax_for(subtotal)
        return {
            "subtotal": subtotal,
            "shipping_cost": shipping,
            "tax": tax,
            "total": subtotal + shipping + tax,
        }

    @staticmethod
    def validate_items(items) -> list[str]:
        """Return a list of human-readable problems with the given items."""
        errors: list[str] = []
        for item in items:
            product = item.product
            if not product.is_active:
                errors.append(f"'{product.name}' is no longer available.")
            elif product.current_price is None or product.current_price <= 0:
                errors.append(f"'{product.name}' has an invalid price.")
            elif item.quantity > product.stock_quantity:
                errors.append(
                    f"Only {product.stock_quantity} of '{product.name}' "
                    f"are in stock (you requested {item.quantity})."
                )
        return errors

    @staticmethod
    @transaction.atomic
    def create_order(
        *,
        user,
        cart_items,
        shipping_address,
        billing_address=None,
        payment_method: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[Order, bool]:
        """Create an order from cart items inside a transaction.

        Args:
            user: The ordering user.
            cart_items: A ``CartItem`` queryset to convert into an order.
            shipping_address: The :class:`~apps.accounts.models.Address`.
            billing_address: Optional billing address.
            payment_method: One of :class:`Order.PaymentMethod`.
            idempotency_key: Optional key to make repeated submissions safe.

        Returns:
            A ``(order, created)`` tuple. ``created`` is False when an existing
            order was returned for a duplicate ``idempotency_key``.

        Raises:
            EmptyCartError: When there are no items.
            CartValidationError: When any item is unavailable, mispriced, or
                short on stock.
        """
        if idempotency_key:
            existing = Order.objects.filter(
                idempotency_key=idempotency_key, user=user
            ).first()
            if existing is not None:
                return existing, False

        items = list(cart_items)
        if not items:
            raise EmptyCartError()

        product_ids = [item.product_id for item in items]
        locked = {
            p.id: p
            for p in Product.objects.select_for_update().filter(id__in=product_ids)
        }

        errors: list[str] = []
        for item in items:
            product = locked.get(item.product_id)
            if product is None or not product.is_active:
                errors.append(
                    f"'{item.product.name}' is no longer available."
                )
            elif product.current_price <= 0:
                errors.append(f"'{product.name}' has an invalid price.")
            elif item.quantity > product.stock_quantity:
                errors.append(
                    f"Only {product.stock_quantity} of '{product.name}' "
                    f"are in stock (you requested {item.quantity})."
                )
        if errors:
            raise CartValidationError(errors)

        subtotal = _money(
            sum(
                (locked[item.product_id].current_price * item.quantity for item in items),
                ZERO,
            )
        )
        shipping = OrderService._shipping_for(subtotal)
        tax = OrderService._tax_for(subtotal)
        total = subtotal + shipping + tax

        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            subtotal=subtotal,
            shipping_cost=shipping,
            tax=tax,
            total=total,
            shipping_address=shipping_address,
            billing_address=billing_address or shipping_address,
            payment_method=payment_method or Order.PaymentMethod.MOCK_CARD,
            idempotency_key=idempotency_key or None,
        )

        for item in items:
            product = locked[item.product_id]
            unit_price = product.current_price
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_sku=product.sku,
                quantity=item.quantity,
                unit_price=unit_price,
                total_price=_money(unit_price * item.quantity),
            )
            OrderService._decrement_stock(product, item.quantity)

        OrderStatusHistory.objects.create(
            order=order, status=Order.Status.PENDING, notes="Order created"
        )

        CartItem.objects.filter(id__in=[item.id for item in items]).delete()
        return order, True

    @staticmethod
    def _decrement_stock(product: Product, quantity: int) -> None:
        """Reduce product (and inventory) stock by ``quantity``."""
        product.stock_quantity = max(product.stock_quantity - quantity, 0)
        product.save(update_fields=["stock_quantity", "updated_at"])

        inventory = getattr(product, "inventory", None)
        if inventory is not None:
            inventory.quantity = max(inventory.quantity - quantity, 0)
            inventory.save(update_fields=["quantity"])

    @staticmethod
    def _restore_stock(order: Order) -> None:
        """Add the order's quantities back to product/inventory stock."""
        for item in order.items.select_related("product"):
            product = item.product
            if product is None:
                continue
            product.stock_quantity += item.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])
            inventory = getattr(product, "inventory", None)
            if inventory is not None:
                inventory.quantity += item.quantity
                inventory.save(update_fields=["quantity"])

    # Allowed status transitions. ``PAID`` is intentionally NOT reachable via
    # ``transition`` — only PaymentService (on provider confirmation) may set it.
    _TRANSITIONS = {
        Order.Status.PENDING: {Order.Status.CANCELLED},
        Order.Status.PAID: {
            Order.Status.SHIPPED,
            Order.Status.REFUNDED,
            Order.Status.CANCELLED,
        },
        Order.Status.SHIPPED: {Order.Status.DELIVERED, Order.Status.REFUNDED},
        Order.Status.DELIVERED: {Order.Status.REFUNDED},
        Order.Status.CANCELLED: set(),
        Order.Status.REFUNDED: set(),
    }

    @staticmethod
    @transaction.atomic
    def transition(
        order: Order,
        new_status: str,
        notes: str = "",
        changed_by=None,
        enforce: bool = True,
    ) -> Order:
        """Move an order to ``new_status`` and record history."""
        if enforce and new_status not in OrderService._TRANSITIONS.get(
            order.status, set()
        ):
            raise OrderError(
                f"Cannot change order status from '{order.get_status_display()}' "
                f"to '{dict(Order.Status.choices).get(new_status, new_status)}'."
            )
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order, status=new_status, notes=notes, changed_by=changed_by
        )
        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order, changed_by=None) -> Order:
        """Cancel (or refund) an order and restore its stock."""
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status == Order.Status.PENDING:
            OrderService._restore_stock(order)
            return OrderService.transition(
                order, Order.Status.CANCELLED, "Cancelled by user", changed_by
            )
        if order.status == Order.Status.PAID:
            OrderService._restore_stock(order)
            return OrderService.transition(
                order, Order.Status.REFUNDED, "Refunded after cancellation", changed_by
            )
        raise OrderError("This order can no longer be cancelled.")


class PaymentService:
    """Process payments for orders and record the outcome.

    This is the **only** code path allowed to mark an order as paid, and it
    does so exclusively on a provider-confirmed success.
    """

    @staticmethod
    @transaction.atomic
    def process_payment(
        order: Order,
        *,
        token: str | None = None,
        provider_name: str | None = None,
    ) -> Payment:
        """Attempt payment for ``order`` and return the :class:`Payment`.

        Idempotent: if the order is already paid, no new charge is made and the
        most recent successful payment is returned.

        Args:
            order: The order to pay for.
            token: Opaque payment-method token (never card data).
            provider_name: Optional provider override.

        Returns:
            The :class:`Payment` record. Check ``payment.succeeded``.
        """
        order = Order.objects.select_for_update().get(pk=order.pk)

        if order.is_paid:
            return order.payments.filter(status=Payment.Status.SUCCEEDED).first()

        provider = get_payment_provider(provider_name)
        payment = Payment.objects.create(
            order=order,
            provider=provider.name,
            amount=order.total,
            status=Payment.Status.PENDING,
        )

        result = provider.charge(order=order, amount=order.total, token=token)

        if result.success:
            payment.mark_succeeded(result.transaction_id, result.raw)
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
            OrderStatusHistory.objects.create(
                order=order,
                status=Order.Status.PAID,
                notes=f"Payment confirmed ({provider.name})",
            )
        else:
            payment.mark_failed(result.message, result.raw)

        return payment

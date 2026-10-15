"""
Orders views: cart, checkout, payment and order history.

Views stay thin: validation and stock/payment logic live in ``services.py``.
"""

from __future__ import annotations

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.catalog.models import Product

from .exceptions import (
    CartValidationError,
    EmptyCartError,
    InsufficientStockError,
    OrderError,
)
from .forms import AddToCartForm, CartUpdateForm, CheckoutForm
from .models import Order
from .services import CartService, OrderService, PaymentService

CHECKOUT_SESSION_KEY = "checkout_idempotency_key"


def _cart_context(request) -> dict:
    """Build the shared cart context (items + totals)."""
    items = CartService.get_cart_items(request)
    totals = OrderService.calculate_totals(items)
    return {
        "cart_items": items,
        "cart_count": CartService.get_item_count(request),
        **totals,
    }


def cart_view(request):
    """Display the shopping cart with totals."""
    return render(request, "orders/cart.html", _cart_context(request))


@require_POST
def cart_add(request, slug: str):
    """Add a product to the cart (works for guests and authenticated users)."""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a valid quantity.")
        return redirect(product.get_absolute_url())

    try:
        CartService.add_to_cart(request, product, form.cleaned_data["quantity"])
    except InsufficientStockError as exc:
        messages.error(request, exc.message)
        return redirect("orders:cart")

    messages.success(request, f"Added '{product.name}' to your cart.")
    return redirect("orders:cart")


@require_POST
def cart_update(request, item_id: int):
    """Update the quantity of a cart line."""
    form = CartUpdateForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a valid quantity.")
        return redirect("orders:cart")

    try:
        CartService.update_quantity(request, item_id, form.cleaned_data["quantity"])
    except (OrderError, InsufficientStockError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    else:
        messages.success(request, "Cart updated.")
    return redirect("orders:cart")


@require_POST
def cart_remove(request, item_id: int):
    """Remove a line from the cart."""
    try:
        CartService.remove_item(request, item_id)
    except OrderError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "Item removed from your cart.")
    return redirect("orders:cart")


@login_required
def checkout_view(request):
    """Show the order summary and place an order (with payment)."""
    cart_items = CartService.get_cart_items(request)
    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("orders:cart")

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            ship_to = form.get_shipping_address()
            key = (
                form.cleaned_data.get("idempotency_key")
                or request.session.get(CHECKOUT_SESSION_KEY)
                or uuid.uuid4().hex
            )
            try:
                order, created = OrderService.create_order(
                    user=request.user,
                    cart_items=cart_items,
                    shipping_address=ship_to,
                    billing_address=ship_to,
                    payment_method=form.cleaned_data["payment_method"],
                    idempotency_key=key,
                )
            except EmptyCartError:
                messages.error(request, "Your cart is empty.")
                return redirect("orders:cart")
            except CartValidationError as exc:
                for error in exc.errors:
                    messages.error(request, error)
                return redirect("orders:cart")

            request.session.pop(CHECKOUT_SESSION_KEY, None)

            if form.cleaned_data["payment_method"] == Order.PaymentMethod.CASH_ON_DELIVERY:
                messages.success(request, "Order placed. Pay when it arrives.")
                return redirect("orders:order_confirmation", pk=order.pk)

            payment = PaymentService.process_payment(
                order, token=form.cleaned_data.get("payment_token")
            )
            if payment is not None and payment.succeeded:
                messages.success(request, "Order placed and payment confirmed.")
                return redirect("orders:order_confirmation", pk=order.pk)

            reason = payment.failure_reason if payment else "Payment was not confirmed."
            messages.error(
                request,
                f"We could not confirm your payment: {reason} "
                "You can retry payment from your order page.",
            )
            return redirect("orders:order_detail", pk=order.pk)
    else:
        key = request.session.get(CHECKOUT_SESSION_KEY) or uuid.uuid4().hex
        request.session[CHECKOUT_SESSION_KEY] = key
        form = CheckoutForm(user=request.user, initial={"idempotency_key": key})

    context = {
        **_cart_context(request),
        "form": form,
        "default_address": request.user.addresses.filter(is_default=True).first(),
    }
    return render(request, "orders/checkout.html", context)


@login_required
@require_POST
def order_pay(request, pk):
    """Retry payment for a pending order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.is_paid:
        messages.info(request, "This order is already paid.")
        return redirect("orders:order_detail", pk=order.pk)

    token = (request.POST.get("payment_token") or "").strip()
    payment = PaymentService.process_payment(order, token=token)
    if payment is not None and payment.succeeded:
        messages.success(request, "Payment confirmed.")
        return redirect("orders:order_confirmation", pk=order.pk)

    reason = payment.failure_reason if payment else "Payment was not confirmed."
    messages.error(request, f"Payment failed: {reason}")
    return redirect("orders:order_detail", pk=order.pk)


@login_required
@require_POST
def order_cancel(request, pk):
    """Cancel a pending/paid order and restore stock."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    try:
        OrderService.cancel_order(order, changed_by=request.user)
    except OrderError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, "Order cancelled.")
    return redirect("orders:order_detail", pk=order.pk)


class OrderConfirmationView(LoginRequiredMixin, DetailView):
    """Post-purchase confirmation page."""

    model = Order
    template_name = "orders/order_confirmation.html"
    context_object_name = "order"

    def get_object(self, queryset=None) -> Order:
        return get_object_or_404(Order, pk=self.kwargs["pk"], user=self.request.user)


class OrderListView(LoginRequiredMixin, ListView):
    """Paginated order history for the current user."""

    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items", "payments")
            .order_by("-created_at")
        )


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Order detail with items, totals, status history and payment info."""

    model = Order
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_object(self, queryset=None) -> Order:
        order = get_object_or_404(
            Order.objects.prefetch_related(
                "items__product", "status_history", "payments"
            ),
            pk=self.kwargs["pk"],
            user=self.request.user,
        )
        return order

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_payment"] = self.object.latest_payment
        return context


def order_lookup_or_404(user, pk):
    """Helper kept for API parity/testing convenience."""
    order = Order.objects.filter(pk=pk, user=user).first()
    if order is None:
        raise Http404("Order not found")
    return order

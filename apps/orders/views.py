"""
Orders views: cart, checkout, order history.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from apps.catalog.models import Product

from .models import CartItem, Order, OrderItem


def cart_view(request):
    """Display shopping cart contents."""
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related("product")
    else:
        cart_items = CartItem.objects.filter(
            session_key=request.session.session_key
        ).select_related("product")

    context = {
        "cart_items": cart_items,
        "cart_total": sum(item.product.current_price * item.quantity for item in cart_items),
    }
    return render(request, "orders/cart.html", context)


@login_required
def checkout_view(request):
    """Checkout page — requires login."""
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")

    if not cart_items.exists():
        return redirect("orders:cart")

    # Calculate totals
    subtotal = sum(item.product.current_price * item.quantity for item in cart_items)
    shipping_cost = 0 if subtotal > 50 else 5.99
    tax = round(subtotal * 0.08, 2)
    total = subtotal + shipping_cost + tax

    context = {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "tax": tax,
        "total": total,
    }
    return render(request, "orders/checkout.html", context)


class OrderListView(LoginRequiredMixin, ListView):
    """User order history."""

    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Order detail page."""

    model = Order
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "items", "status_history"
        )

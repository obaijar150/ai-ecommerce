"""
Orders API views (DRF): cart management and read-only orders.
"""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Address

from .exceptions import CartValidationError, EmptyCartError, OrderError
from .models import CartItem, Order
from .serializers import CartItemSerializer, OrderSerializer
from .services import CartService, OrderService, PaymentService


def _error(message: str, code: str = "cart_error") -> dict:
    """Return a DRF-style error payload."""
    return {"error": {"code": code, "message": message}}


class CartViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated user's cart, plus checkout.

    All stock validation is delegated to ``CartService``/``OrderService``.
    """

    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the requesting user's cart items."""
        return CartItem.objects.filter(user=self.request.user).select_related(
            "product"
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)
        try:
            item = CartService.add_to_cart(request, product, quantity)
        except OrderError as exc:
            return Response(
                _error(getattr(exc, "message", str(exc))),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.get_serializer(item).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data.get("quantity", item.quantity)
        try:
            CartService.update_quantity(request, item.id, quantity)
        except OrderError as exc:
            return Response(
                _error(getattr(exc, "message", str(exc))),
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.refresh_from_db()
        return Response(self.get_serializer(item).data)

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        try:
            CartService.remove_item(request, item.id)
        except OrderError as exc:
            return Response(
                _error(getattr(exc, "message", str(exc))),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """Create an order from the cart and attempt payment."""
        address = Address.objects.filter(
            pk=request.data.get("shipping_address"), user=request.user
        ).first()
        if address is None:
            return Response(
                _error("A valid shipping address is required.", "invalid_address"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items = self.get_queryset()
        try:
            order, _created = OrderService.create_order(
                user=request.user,
                cart_items=cart_items,
                shipping_address=address,
                billing_address=address,
                payment_method=request.data.get(
                    "payment_method", Order.PaymentMethod.MOCK_CARD
                ),
                idempotency_key=request.data.get("idempotency_key"),
            )
        except EmptyCartError as exc:
            return Response(
                _error(exc.message, "empty_cart"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CartValidationError as exc:
            return Response(
                _error(" ".join(exc.errors), "cart_validation"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = PaymentService.process_payment(
            order, token=request.data.get("payment_token")
        )
        order.refresh_from_db()
        return Response(
            OrderSerializer(order).data, status=status.HTTP_201_CREATED
        )


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API endpoint for the authenticated user's orders."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only access their own orders."""
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items", "payments")
            .order_by("-created_at")
        )

"""
Orders serializers (DRF).

Serializers never expose sensitive data. Card numbers and CVV values are not
stored anywhere and therefore can never appear in a response.
"""

from rest_framework import serializers

from apps.catalog.models import Product

from .models import CartItem, Order, OrderItem, Payment


class CartItemSerializer(serializers.ModelSerializer):
    """Read/write serializer for a cart line."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    line_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_slug",
            "quantity",
            "unit_price",
            "line_total",
            "added_at",
        ]
        read_only_fields = ["id", "added_at"]

    def validate_quantity(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate_product(self, value: Product) -> Product:
        if not value.is_active:
            raise serializers.ValidationError("This product is not available.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """Read-only payment summary (no sensitive data)."""

    class Meta:
        model = Payment
        fields = [
            "id",
            "provider",
            "transaction_id",
            "amount",
            "status",
            "failure_reason",
            "created_at",
            "confirmed_at",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    product_name_display = serializers.CharField(
        source="display_name", read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_name_display",
            "product_sku",
            "quantity",
            "unit_price",
            "total_price",
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Read-only serializer for Order model."""

    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    short_id = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "short_id",
            "status",
            "status_display",
            "subtotal",
            "tax",
            "shipping_cost",
            "total",
            "payment_method",
            "paid_at",
            "tracking_number",
            "items",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

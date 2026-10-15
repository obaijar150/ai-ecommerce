"""
Orders serializers (DRF).
"""

from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "unit_price", "total_price"]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""

    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "status_display",
            "subtotal",
            "tax",
            "shipping_cost",
            "total",
            "payment_method",
            "tracking_number",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total", "status"]

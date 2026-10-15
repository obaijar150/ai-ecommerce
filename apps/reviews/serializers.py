"""
Reviews serializers (DRF).
"""

from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model."""

    username = serializers.CharField(source="user.username", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "product",
            "product_name",
            "user",
            "username",
            "rating",
            "title",
            "body",
            "is_verified_purchase",
            "helpful_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "helpful_count", "is_verified_purchase"]

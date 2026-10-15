"""
Accounts serializers (DRF).
"""

from rest_framework import serializers

from .models import Profile, Address, WishlistItem


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile model."""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "avatar",
            "bio",
            "date_of_birth",
            "newsletter_subscribed",
        ]


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model."""

    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "street",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
        ]


class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer for WishlistItem model."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_price = serializers.DecimalField(
        source="product.current_price", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = WishlistItem
        fields = ["id", "product_name", "product_slug", "product_price", "added_at"]

"""
Catalog serializers (DRF).
"""

from rest_framework import serializers

from .models import Category, Product, ProductImage, Tag


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "children", "is_active"]

    def get_children(self, obj):
        """Serialize child categories."""
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model."""

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary"]


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "category_name",
            "price",
            "sale_price",
            "current_price",
            "discount_percentage",
            "sku",
            "stock_quantity",
            "in_stock",
            "is_active",
            "is_featured",
            "average_rating",
            "review_count",
            "view_count",
            "tags",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["average_rating", "review_count", "view_count"]

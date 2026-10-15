"""
Catalog serializers (DRF).
"""

from rest_framework import serializers

from .models import Brand, Category, Product, ProductImage, Tag


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for Brand model."""

    product_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "description", "logo", "website", "product_count"]


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model with nested children."""

    children = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "children", "product_count", "is_active"]

    def get_children(self, obj):
        """Serialize child categories recursively."""
        if obj.children.exists():
            return CategorySerializer(obj.children.filter(is_active=True), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model."""

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product list views."""

    primary_image = serializers.SerializerMethodField()
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "sku",
            "category", "category_name", "brand_name",
            "price", "sale_price", "current_price", "discount_percentage",
            "stock_quantity", "in_stock",
            "average_rating", "review_count",
            "is_featured", "primary_image",
        ]

    def get_primary_image(self, obj):
        image = obj.primary_image
        if image:
            request = self.context.get("request")
            url = image.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for product detail views."""

    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description",
            "category", "category_name", "brand", "brand_name",
            "price", "sale_price", "current_price", "discount_percentage",
            "sku", "stock_quantity", "in_stock", "weight_kg",
            "specifications", "tags", "images",
            "average_rating", "review_count", "view_count",
            "is_active", "is_featured",
            "created_at", "updated_at",
        ]

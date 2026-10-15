"""
Catalog API views (DRF ViewSets).
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Brand, Category, Product, Tag
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    TagSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for product categories with nested children."""

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name"]
    filterset_fields = ["parent", "is_active"]


class ProductViewSet(viewsets.ModelViewSet):
    """API endpoint for products with filtering and search."""

    queryset = Product.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "brand", "is_featured", "stock_quantity"]
    search_fields = ["name", "description", "sku", "brand__name"]
    ordering_fields = ["price", "created_at", "average_rating", "view_count", "stock_quantity"]

    def get_serializer_class(self):
        """Use detail serializer for retrieve, list for others."""
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer


class BrandViewSet(viewsets.ModelViewSet):
    """API endpoint for product brands."""

    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name"]


class TagViewSet(viewsets.ModelViewSet):
    """API endpoint for product tags."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name"]

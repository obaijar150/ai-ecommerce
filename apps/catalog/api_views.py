"""
Catalog API views (DRF ViewSets).
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import Category, Product, Tag
from .serializers import CategorySerializer, ProductSerializer, TagSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for product categories."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name"]
    filterset_fields = ["parent", "is_active"]


class ProductViewSet(viewsets.ModelViewSet):
    """API endpoint for products."""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "is_featured", "price"]
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["price", "created_at", "average_rating", "view_count"]


class TagViewSet(viewsets.ModelViewSet):
    """API endpoint for product tags."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name"]

"""
Catalog API URL patterns (DRF).
"""

app_name = "api_catalog"

from django.urls import path  # noqa: F401
from rest_framework.routers import DefaultRouter

from .api_views import BrandViewSet, CategoryViewSet, ProductViewSet, TagViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = router.urls

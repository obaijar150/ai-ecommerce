"""
Catalog API URL patterns (DRF).
"""

app_name = "api_catalog"

from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import CategoryViewSet, ProductViewSet, TagViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = router.urls

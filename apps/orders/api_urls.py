"""
Orders API URL patterns (DRF).
"""

app_name = "api_orders"

from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import CartViewSet, OrderViewSet

router = DefaultRouter()
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = router.urls

"""
Reviews API URL patterns (DRF).
"""

app_name = "api_reviews"

from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import ReviewViewSet

router = DefaultRouter()
router.register(r"reviews", ReviewViewSet, basename="review")

urlpatterns = router.urls

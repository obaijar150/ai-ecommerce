"""
Accounts API URL patterns (DRF).
"""

app_name = "api_accounts"

from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import ProfileViewSet

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")

urlpatterns = router.urls

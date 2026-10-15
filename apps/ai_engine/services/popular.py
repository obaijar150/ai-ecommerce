"""
Popularity-based recommendation service (fallback for cold start).
"""

from typing import List

from apps.catalog.models import Product
from apps.ai_engine.models import RecommendationCache


class PopularityService:
    """Service for popularity-based recommendations (cold start fallback)."""

    @staticmethod
    def get_popular_products(limit: int = 10) -> List[Product]:
        """Return most popular products by view count and rating."""
        return list(
            Product.objects.filter(is_active=True)
            .order_by("-view_count", "-average_rating")[:limit]
        )

    @staticmethod
    def get_trending_products(limit: int = 10) -> List[Product]:
        """Return trending products (recently viewed/purchased)."""
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        recent_date = timezone.now() - timedelta(days=7)

        return list(
            Product.objects.filter(
                is_active=True,
                activity_logs__created_at__gte=recent_date,
            )
            .annotate(activity_count=Count("activity_logs"))
            .order_by("-activity_count")[:limit]
        )

"""
Recommendation service: collaborative filtering via Surprise SVD.

Falls back to popularity-based recommendations for new users (cold start).
"""

import logging
from typing import List, Optional

from django.contrib.auth import get_user_model

from apps.catalog.models import Product
from apps.ai_engine.models import RecommendationCache

logger = logging.getLogger(__name__)
User = get_user_model()


class RecommendationService:
    """Service for generating and retrieving product recommendations."""

    DEFAULT_LIMIT = 10

    @staticmethod
    def get_recommendations(
        user=None,
        session_key: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[RecommendationCache]:
        """
        Get personalized product recommendations.

        For authenticated users: returns cached SVD-based recommendations.
        For guests or cold start: returns popular products.
        """
        if user and user.is_authenticated:
            # Check cache first
            cached = RecommendationCache.objects.filter(
                user=user
            ).select_related("product")[:limit]

            if cached:
                return cached

            # Cache miss — generate on the fly (or trigger Celery task)
            return RecommendationService._get_popular_recommendations(user, limit)

        # Guest user — popular products
        return RecommendationService._get_popular_recommendations(None, limit)

    @staticmethod
    def _get_popular_recommendations(
        user, limit: int
    ) -> List[RecommendationCache]:
        """Fallback: return most popular products as recommendations."""
        popular_products = Product.objects.filter(is_active=True).order_by(
            "-view_count", "-average_rating"
        )[:limit]

        # Create RecommendationCache entries with popularity score
        recommendations = []
        for rank, product in enumerate(popular_products, 1):
            rec, _ = RecommendationCache.objects.get_or_create(
                user=user if user and user.is_authenticated else None,
                product=product,
                defaults={
                    "score": round(1.0 / rank, 4),
                    "algorithm": "popular",
                    "rank": rank,
                },
            )
            recommendations.append(rec)

        return recommendations

    @staticmethod
    def train_svd_model() -> dict:
        """
        Train SVD model using scikit-surprise on user activity data.

        Returns:
            dict with training metrics (rmse, mae, coverage)
        """
        try:
            from surprise import Dataset, Reader, SVD
            from surprise.model_selection import cross_validate
            import pandas as pd
            from apps.ai_engine.models import UserActivityLog

            # Build rating dataset from activity logs
            activities = UserActivityLog.objects.filter(
                activity_type__in=["purchase", "rate", "cart_add"]
            ).values("user__id", "product__id", "activity_type")

            if len(activities) < 10:
                logger.warning("Not enough data to train SVD model")
                return {"status": "insufficient_data", "samples": len(activities)}

            # Convert to Surprise format
            ratings = []
            for act in activities:
                rating = {"purchase": 5, "rate": 4, "cart_add": 3}.get(
                    act["activity_type"], 3
                )
                ratings.append((act["user__id"], act["product__id"], rating))

            df = pd.DataFrame(ratings, columns=["uid", "iid", "rating"])
            reader = Reader(rating_scale=(1, 5))
            data = Dataset.load_from_df(df[["uid", "iid", "rating"]], reader)

            # Train SVD
            algo = SVD(n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.02)
            results = cross_validate(algo, data, measures=["RMSE", "MAE"], cv=3)

            logger.info(
                f"SVD model trained — RMSE: {results['test_rmse'].mean():.3f}, "
                f"MAE: {results['test_mae'].mean():.3f}"
            )

            return {
                "status": "trained",
                "rmse": float(results["test_rmse"].mean()),
                "mae": float(results["test_mae"].mean()),
                "samples": len(ratings),
            }

        except Exception as e:
            logger.error(f"SVD training failed: {e}")
            return {"status": "error", "message": str(e)}

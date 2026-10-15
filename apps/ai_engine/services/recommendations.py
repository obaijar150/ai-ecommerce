"""
Recommendation service used by the recommendations API.

Authenticated users get recommendations from the newest trained artifact via the
isolated ``ai_engine.ml`` engine (see ``services/ml_service.py``), cached in
``RecommendationCache``. Guests and cold-start users get a deterministic
popularity ranking that is **not** persisted (``RecommendationCache.user`` is
non-nullable, so there is nothing to key guest rows on).
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

        For authenticated users: returns cached recommendations, generating and
        caching them on a miss. For guests: returns a non-persisted popularity
        ranking (guests have no cache row).
        """
        if user and user.is_authenticated:
            cached = list(
                RecommendationCache.objects.filter(user=user)
                .select_related("product")[:limit]
            )
            if cached:
                return cached
            return RecommendationService._generate_for_user(user, limit)

        # Guest user — popularity ranking, never persisted.
        return RecommendationService._get_popular_recommendations(None, limit)

    @staticmethod
    def _generate_for_user(user, limit: int) -> List[RecommendationCache]:
        """Generate and cache recommendations for an authenticated user.

        Tries the trained ML engine first and falls back to popularity when it
        produces nothing or is unavailable.
        """
        pairs: list = []
        algorithm = "popular"
        try:
            from .ml_service import recommend_products_scored

            pairs, algorithm = recommend_products_scored(user, limit)
        except Exception:
            logger.exception("ML recommendations failed; using popularity fallback.")

        if not pairs:
            return RecommendationService._get_popular_recommendations(user, limit)

        recommendations: List[RecommendationCache] = []
        for rank, (product, score) in enumerate(pairs, 1):
            rec, _ = RecommendationCache.objects.get_or_create(
                user=user,
                product=product,
                defaults={
                    "score": round(float(score), 4),
                    "algorithm": algorithm,
                    "rank": rank,
                },
            )
            recommendations.append(rec)
        return recommendations

    @staticmethod
    def _get_popular_recommendations(
        user, limit: int
    ) -> List[RecommendationCache]:
        """Fallback: return the most popular products as recommendations.

        Rows are persisted only for authenticated users; for guests the
        ``RecommendationCache`` instances are returned unsaved so the response
        works without violating the non-null ``user`` constraint.
        """
        popular_products = Product.objects.filter(is_active=True).order_by(
            "-view_count", "-average_rating"
        )[:limit]

        persist = bool(user and getattr(user, "is_authenticated", False))
        recommendations: List[RecommendationCache] = []
        for rank, product in enumerate(popular_products, 1):
            score = round(1.0 / rank, 4)
            if persist:
                rec, _ = RecommendationCache.objects.get_or_create(
                    user=user,
                    product=product,
                    defaults={
                        "score": score,
                        "algorithm": "popular",
                        "rank": rank,
                    },
                )
            else:
                rec = RecommendationCache(
                    user=None,
                    product=product,
                    score=score,
                    algorithm="popular",
                    rank=rank,
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

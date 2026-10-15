"""
Celery tasks for AI engine: model training, summary generation.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def train_recommendation_model(self):
    """Train SVD recommendation model asynchronously."""
    from apps.ai_engine.services.recommendations import RecommendationService

    try:
        result = RecommendationService.train_svd_model()
        logger.info(f"Recommendation model training completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Recommendation model training failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_review_summary(self, product_id: str):
    """Generate AI review summary for a product asynchronously."""
    from apps.catalog.models import Product
    from apps.reviews.services import ReviewSummarizationService

    try:
        product = Product.objects.get(id=product_id)
        summary = ReviewSummarizationService.generate_summary(product)
        if summary:
            logger.info(f"Generated review summary for {product.name}")
            return {"product_id": product_id, "status": "success"}
        else:
            return {"product_id": product_id, "status": "no_reviews"}
    except Product.DoesNotExist:
        logger.warning(f"Product {product_id} not found for summary generation")
        return {"product_id": product_id, "status": "not_found"}
    except Exception as exc:
        logger.error(f"Summary generation failed for {product_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def clear_old_activity_logs(days: int = 90):
    """Clean up old activity logs to prevent database bloat."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.ai_engine.models import UserActivityLog

    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = UserActivityLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    logger.info(f"Deleted {deleted_count} old activity log entries")
    return deleted_count

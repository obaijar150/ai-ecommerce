"""
Reviews models: Review, ReviewSummary (AI-generated).
"""

from django.conf import settings
from django.db import models


class Review(models.Model):
    """Product review with rating and text."""

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["product", "user"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.rating}★ on {self.product.name}"


class ReviewSummary(models.Model):
    """AI-generated summary of all reviews for a product."""

    product = models.OneToOneField(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="ai_summary",
    )
    summary = models.TextField()
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    model_version = models.CharField(max_length=50, default="nltk-v1")
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"AI Summary for {self.product.name}"

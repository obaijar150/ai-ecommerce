"""
Search models: SearchQueryLog for analytics.
"""

from django.conf import settings
from django.db import models


class SearchQueryLog(models.Model):
    """Log search queries for analytics and improvement."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    query = models.CharField(max_length=500)
    results_count = models.PositiveIntegerField(default=0)
    clicked_product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Search: '{self.query[:50]}' ({self.results_count} results)"

"""
AI Engine models: RecommendationCache, ChatSession, ChatMessage, UserActivityLog.
"""

from django.conf import settings
from django.db import models


class RecommendationCache(models.Model):
    """Cached AI-generated product recommendations per user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_recommendations",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="recommended_to",
    )
    score = models.DecimalField(max_digits=5, decimal_places=4)
    algorithm = models.CharField(max_length=50, default="svd")
    rank = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user", "-score"]
        unique_together = ["user", "product"]

    def __str__(self) -> str:
        return f"Rec for {self.user.username}: {self.product.name} ({self.score})"


class UserActivityLog(models.Model):
    """Track user activities for AI recommendation training."""

    class ActivityType(models.TextChoices):
        VIEW = "view", "View"
        SEARCH = "search", "Search"
        CART_ADD = "cart_add", "Cart Add"
        PURCHASE = "purchase", "Purchase"
        RATE = "rate", "Rate"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="activity_logs",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "activity_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.activity_type} by {self.user.username if self.user else 'guest'}"


class ChatSession(models.Model):
    """AI shopping assistant chat session."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Chat {self.id[:8]}"


class ChatMessage(models.Model):
    """Individual messages within a chat session."""

    class Sender(models.TextChoices):
        USER = "user", "User"
        BOT = "bot", "Bot"

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=10, choices=Sender.choices)
    message = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender}: {self.message[:50]}"

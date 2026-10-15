"""
Django admin configuration for ai_engine app.
"""

from django.contrib import admin

from .models import ChatMessage, ChatSession, RecommendationCache, UserActivityLog


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "score", "algorithm", "rank"]
    list_filter = ["algorithm"]


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ["user", "activity_type", "product", "created_at"]
    list_filter = ["activity_type"]


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "started_at", "ended_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["session", "sender", "message", "intent", "confidence"]
    list_filter = ["sender", "intent"]

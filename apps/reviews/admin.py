"""
Django admin configuration for reviews app.
"""

from django.contrib import admin

from .models import Review, ReviewSummary


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "is_verified_purchase", "helpful_count"]
    list_filter = ["rating", "is_verified_purchase", "created_at"]
    search_fields = ["title", "body", "user__username"]


@admin.register(ReviewSummary)
class ReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ["product", "model_version", "generated_at"]

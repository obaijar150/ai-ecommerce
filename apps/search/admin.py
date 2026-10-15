"""
Django admin configuration for search app.
"""

from django.contrib import admin

from .models import SearchQueryLog


@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ["query", "user", "results_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["query"]

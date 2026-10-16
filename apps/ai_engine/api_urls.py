"""
AI integration API URLs.
"""

from django.urls import path

from . import api_views

app_name = "ai_integration"

urlpatterns = [
    path("ai/search/", api_views.AISearchAPIView.as_view(), name="ai_search"),
    path("ai/search/", api_views.ai_search_post, name="ai_search_post"),
    path("ai/recommendations/", api_views.AIRecommendationsAPIView.as_view(), name="ai_recommendations"),
    path("ai/review-summary/<int:product_id>/", api_views.AIReviewSummaryAPIView.as_view(), name="ai_review_summary"),
    path("ai/support/", api_views.AISupportAPIView.as_view(), name="ai_support"),
]

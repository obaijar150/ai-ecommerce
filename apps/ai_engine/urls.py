"""
AI Engine URL patterns.
"""

from django.urls import path

from . import views

app_name = "ai_engine"

urlpatterns = [
    path("api/chat/", views.ChatAPIView.as_view(), name="chat_api"),
    path(
        "api/recommendations/",
        views.RecommendationsAPIView.as_view(),
        name="recommendations_api",
    ),
]

"""
Search URL patterns.
"""

from django.urls import path

from . import views

app_name = "search"

urlpatterns = [
    path("", views.ProductSearchView.as_view(), name="search_results"),
]

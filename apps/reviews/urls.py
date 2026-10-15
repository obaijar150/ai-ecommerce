"""
Reviews URL patterns.
"""

from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "product/<slug:product_slug>/create/",
        views.review_create,
        name="review_create",
    ),
    path(
        "product/<slug:product_slug>/",
        views.ReviewListView.as_view(),
        name="review_list",
    ),
    path(
        "review/<int:review_id>/helpful/",
        views.mark_helpful,
        name="mark_helpful",
    ),
]

"""Tests for the Django-facing ML service facade."""

from __future__ import annotations

import pytest

from apps.ai_engine.services import ml_service


@pytest.fixture()
def products(db):
    """Create a handful of active catalog products with distinct text."""
    from apps.catalog.tests.factories import CategoryFactory, ProductFactory

    electronics = CategoryFactory(name="Electronics")
    books = CategoryFactory(name="Books")
    created = [
        ProductFactory(
            name="Wireless Headphones",
            description="bluetooth audio headphones for music",
            category=electronics,
        ),
        ProductFactory(
            name="Running Shoes",
            description="lightweight sports footwear for runners",
            category=electronics,
        ),
        ProductFactory(
            name="Cookbook",
            description="recipes for the kitchen and cooking",
            category=books,
        ),
    ]
    return created


@pytest.mark.django_db
def test_recommend_products_uses_activity_fallback(products, artifacts_dir):
    """Without a trained artifact, recommendations come from activity popularity."""
    from django.contrib.auth import get_user_model

    from apps.ai_engine.models import UserActivityLog

    user = get_user_model().objects.create_user(username="rec-user", password="pass12345")
    # Give a strong signal to the first product only.
    UserActivityLog.objects.create(user=user, product=products[0], activity_type="purchase")

    recommendations = ml_service.recommend_products(user, limit=5)
    # The seen product is excluded; other catalog products are returned.
    assert products[0] not in recommendations
    assert all(product.is_active for product in recommendations)


@pytest.mark.django_db
def test_recommend_products_returns_empty_without_data(artifacts_dir):
    """A user with no activity and no catalog yields no recommendations."""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(username="empty-user", password="pass12345")
    assert ml_service.recommend_products(user, limit=5) == []


@pytest.mark.django_db
def test_semantic_search_ranks_relevant_products(products, artifacts_dir):
    """A semantic query surfaces the most textually relevant product first."""
    results = ml_service.semantic_search("wireless bluetooth headphones", limit=3)
    assert results
    top_product, score = results[0]
    assert top_product.name == "Wireless Headphones"
    assert score > 0


@pytest.mark.django_db
def test_semantic_search_ignores_empty_query(products):
    """An empty query returns nothing."""
    assert ml_service.semantic_search("", limit=3) == []


def test_summarize_reviews_returns_text():
    """Review summarization always returns a string."""
    summary = ml_service.summarize_reviews(
        ["Great battery life.", "Sharp camera.", "Slow shipping.", "Good value."]
    )
    assert isinstance(summary, str)
    assert summary

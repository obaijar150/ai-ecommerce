"""
Regression tests for the recommendations endpoint and service.

These guard against the original defect where the guest path tried to persist a
``RecommendationCache`` row with ``user=None``, violating the non-null
constraint and returning HTTP 500.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.ai_engine.models import RecommendationCache
from apps.ai_engine.services.recommendations import RecommendationService


@pytest.fixture()
def catalog_products(db):
    """Create a few active products for recommendation responses."""
    from apps.catalog.tests.factories import ProductFactory

    return [ProductFactory(name=f"Rec Product {i}") for i in range(3)]


@pytest.mark.django_db
def test_guest_recommendations_do_not_persist(catalog_products):
    """The guest path returns popular products without creating cache rows."""
    recommendations = RecommendationService.get_recommendations(user=None, limit=5)
    assert recommendations
    assert RecommendationCache.objects.count() == 0


@pytest.mark.django_db
def test_guest_recommendations_reference_real_products(catalog_products):
    """Guest recommendations resolve to the active catalog products."""
    recommendations = RecommendationService.get_recommendations(user=None, limit=5)
    returned = {rec.product_id for rec in recommendations}
    assert returned == {product.pk for product in catalog_products}


@pytest.mark.django_db
def test_recommendations_api_returns_ok_for_guest(client, catalog_products):
    """The endpoint returns 200 with a JSON payload for anonymous users."""
    response = client.get("/chat/api/recommendations/")
    assert response.status_code == 200
    payload = response.json()
    assert "recommendations" in payload
    assert isinstance(payload["recommendations"], list)
    assert payload["recommendations"]


@pytest.mark.django_db
def test_recommendations_api_for_authenticated_user(client, catalog_products, artifacts_dir):
    """An authenticated request returns 200 and caches its recommendations."""
    user = get_user_model().objects.create_user(
        username="rec-view-user", password="pass12345"
    )
    client.force_login(user)
    response = client.get("/chat/api/recommendations/")
    assert response.status_code == 200
    assert response.json()["recommendations"]


@pytest.mark.django_db
def test_authenticated_cache_is_reused(catalog_products, artifacts_dir):
    """A second call returns the already-cached rows."""
    user = get_user_model().objects.create_user(
        username="rec-cache-user", password="pass12345"
    )
    first = RecommendationService.get_recommendations(user=user, limit=5)
    second = RecommendationService.get_recommendations(user=user, limit=5)
    assert [r.pk for r in first] == [r.pk for r in second]

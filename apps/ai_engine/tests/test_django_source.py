"""Tests for the Django ORM adapters that feed the ML package."""

from __future__ import annotations

import pytest

from apps.ai_engine.ml.data.django_source import (
    load_interactions_from_activity,
    load_item_features,
)


@pytest.mark.django_db
def test_load_item_features_from_catalog():
    """Item features are built from real catalog products."""
    from apps.catalog.tests.factories import BrandFactory, CategoryFactory, ProductFactory

    category = CategoryFactory(name="Test Category")
    brand = BrandFactory(name="Test Brand")
    product = ProductFactory(
        name="Test Widget",
        category=category,
        brand=brand,
    )
    features = load_item_features()
    assert str(product.pk) in features
    assert features[str(product.pk)]["name"] == "Test Widget"
    assert features[str(product.pk)]["brand"] == "Test Brand"
    assert "Test Widget" in features[str(product.pk)]["text"]


@pytest.mark.django_db
def test_load_interactions_from_activity():
    """Activity rows become weighted interactions."""
    from django.contrib.auth import get_user_model

    from apps.ai_engine.models import UserActivityLog
    from apps.catalog.tests.factories import ProductFactory

    user = get_user_model().objects.create_user(
        username="ml-user", password="pass12345"
    )
    product = ProductFactory()
    UserActivityLog.objects.create(user=user, product=product, activity_type="purchase")

    rows = load_interactions_from_activity()
    assert rows
    assert rows[0]["item_id"] == str(product.pk)
    assert rows[0]["weight"] == 5.0


@pytest.mark.django_db
def test_load_interactions_ignores_null_products():
    """Activity rows without a product are skipped."""
    from django.contrib.auth import get_user_model

    from apps.ai_engine.models import UserActivityLog

    user = get_user_model().objects.create_user(
        username="ml-user-2", password="pass12345"
    )
    UserActivityLog.objects.create(user=user, product=None, activity_type="search")
    assert load_interactions_from_activity() == []

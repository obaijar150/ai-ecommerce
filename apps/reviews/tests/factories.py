"""
Test factories for the reviews app.
"""

import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import ProductFactory

from apps.reviews.models import Review


class ReviewFactory(DjangoModelFactory):
    """Factory for creating test reviews."""

    class Meta:
        model = Review

    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    rating = 5
    title = "Great product"
    body = "Would buy again."
    is_verified_purchase = False

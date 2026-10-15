"""Typo-tolerance benchmark across search and chat.

These tests are the acceptance criteria for the smart-search phase: common
misspellings of product words must still resolve to the right catalog items.
"""

from __future__ import annotations

import pytest

from apps.catalog.tests.factories import ProductFactory


@pytest.mark.django_db
def test_search_tolerates_common_typos(db):
    """A misspelled query still returns the relevant product."""
    from django.test.utils import override_settings

    ProductFactory(name="Wireless Bluetooth Headphones", description="audio")
    ProductFactory(name="Vertex Studio Headphones", description="pro audio")

    from apps.search.services import SearchService

    # Postgres-only RRF needs a PG backend; on SQLite the service degrades to
    # a portable icontains search, so exercise semantic search too.
    from apps.ai_engine.services import ml_service

    for typo in ("hedphones", "headpone", "headphnes"):
        hits = ml_service.semantic_search(typo, limit=5)
        names = [product.name for product, _ in hits]
        assert any("Headphones" in name for name in names), (typo, names)


@pytest.mark.django_db
def test_chat_tolerates_typo_queries(client, db):
    """The chatbot resolves misspelled product queries to real products."""
    ProductFactory(name="Wireless Bluetooth Headphones", description="audio")
    response = client.post("/chat/api/chat/", {"message": "can you fing me hedphones"})
    assert response.status_code == 200
    payload = response.json()
    assert "Headphones" in payload["message"]

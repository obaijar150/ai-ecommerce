"""Tests for the smarter AI chatbot (intent, grounding, graceful fallbacks)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.ai_engine.services.chatbot import ChatbotService


@pytest.mark.parametrize(
    "message,expected",
    [
        ("hello", "greeting"),
        ("hi there", "greeting"),
        ("help", "help"),
        ("what can you do", "help"),
        ("find a smartphone", "product_search"),
        ("show me headphones", "product_search"),
        ("recommend something", "recommendation"),
        ("suggest a gift", "recommendation"),
        ("where is my order", "order_status"),
        ("track my package", "order_status"),
        ("summarize the reviews", "review_summary"),
        ("product ratings", "review_summary"),
    ],
)
def test_classify_intent(message, expected):
    """Intent classification maps common phrasings to the right bucket."""
    intent, confidence = ChatbotService.classify_intent(message)
    assert intent == expected
    assert 0 < confidence <= 1.0


def test_classify_intent_empty_returns_fallback():
    """An empty message yields the fallback intent."""
    intent, _ = ChatbotService.classify_intent("")
    assert intent == "fallback"


@pytest.mark.django_db
def test_product_search_response_lists_real_products(client, db):
    """A product search returns real matching catalog products."""
    from apps.catalog.tests.factories import ProductFactory

    ProductFactory(name="Wireless Bluetooth Headphones", description="audio")
    response = client.post("/chat/api/chat/", {"message": "find headphones"})
    assert response.status_code == 200
    payload = response.json()
    assert "Wireless Bluetooth Headphones" in payload["message"]
    assert payload["intent"] == "product_search"


@pytest.mark.django_db
def test_greeting_response_is_friendly(client, db):
    """Greeting produces a non-empty welcome message."""
    response = client.post("/chat/api/chat/", {"message": "hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "greeting"
    assert "shopping assistant" in payload["message"].lower()


@pytest.mark.django_db
def test_help_lists_capabilities(client, db):
    """Help response enumerates the assistant's capabilities."""
    response = client.post("/chat/api/chat/", {"message": "help"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "help"
    assert "Finding products" in payload["message"]


@pytest.mark.django_db
def test_order_status_requires_login(client, db):
    """Anonymous users are prompted to log in / provide an order number."""
    response = client.post("/chat/api/chat/", {"message": "where is my order"})
    assert response.status_code == 200
    payload = response.json()
    assert "log in" in payload["message"].lower() or "order number" in payload["message"].lower()


@pytest.mark.django_db
def test_fallback_retries_as_product_search(client, db):
    """A near-miss product query is retried as a search before giving up."""
    from apps.catalog.tests.factories import ProductFactory

    ProductFactory(name="Quantum Espresso Maker", description="coffee")
    response = client.post("/chat/api/chat/", {"message": "quantum espresso"})
    assert response.status_code == 200
    payload = response.json()
    assert "Quantum Espresso Maker" in payload["message"]


@pytest.mark.django_db
def test_recommendations_for_authenticated_user(client, db, artifacts_dir):
    """Authenticated users get a recommendation list (never a crash)."""
    from apps.catalog.tests.factories import ProductFactory

    ProductFactory(name="Rec Product", description="travel gear")
    user = get_user_model().objects.create_user(username="chat-user", password="pass12345")
    client.force_login(user)
    response = client.post("/chat/api/chat/", {"message": "recommend something"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommendation"
    assert "Rec Product" in payload["message"] or "popular" in payload["message"].lower()

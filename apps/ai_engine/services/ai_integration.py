"""
Constraint-aware semantic product search, recommendation explanations,
review summarization with caching, and permissions-aware support RAG.

This module wires the isolated ML package into Django without bypassing the ORM:
every product, price, stock value and order status returned to the client comes
from the database, never from a model.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.db.models import Q

from apps.catalog.models import Product
from apps.ai_engine.services.ai_search import ai_search
from apps.ai_engine.services.ml_service import recommend_products, semantic_search
from apps.ai_engine.services.constraints import extract_constraints

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Recommendations with explanations
# --------------------------------------------------------------------------- #
def explained_recommendations(user, limit: int = 8) -> list[dict[str, Any]]:
    """Return recommended products together with human-readable reasons.

    Reasons are derived from *real* product features and the user's actual
    interaction history; nothing is invented by a language model.
    """
    products = recommend_products(user, limit=limit) if user and getattr(user, "is_authenticated", False) else []
    if not products:
        products = list(
            Product.objects.filter(is_active=True, stock_quantity__gt=0)
            .order_by("-view_count", "-average_rating")[:limit]
        )

    seen_ids = set()
    if user and getattr(user, "is_authenticated", False):
        try:
            from apps.ai_engine.models import UserActivityLog

            seen_ids = set(
                UserActivityLog.objects.filter(user=user, product__isnull=False)
                .values_list("product_id", flat=True)
            )
        except Exception:
            seen_ids = set()

    results: list[dict[str, Any]] = []
    for product in products:
        if getattr(product, "stock_quantity", 0) <= 0:
            continue
        reasons: list[str] = []
        if product.pk in seen_ids:
            reasons.append("related to products you have interacted with")
        if getattr(product, "is_featured", False):
            reasons.append("featured by the store")
        if getattr(product, "average_rating", 0) and float(product.average_rating) >= 4:
            reasons.append(f"highly rated ({product.average_rating}/5)")
        category = getattr(product, "category", None)
        if category is not None:
            reasons.append(f"belongs to {category.name}")
        if getattr(product, "view_count", 0) and product.view_count > 50:
            reasons.append("popular with shoppers")
        if not reasons:
            reasons.append("matches your interests")
        results.append(
            {
                "product_id": str(product.pk),
                "name": product.name,
                "slug": product.slug,
                "price": str(product.current_price),
                "stock_quantity": product.stock_quantity,
                "score": None,
                "reasons": reasons,
                "url": f"/products/{product.slug}/",
            }
        )
    return results[:limit]


# --------------------------------------------------------------------------- #
# Review summarization (cached)
# --------------------------------------------------------------------------- #
def _themes(reviews: list[str], top_n: int = 5) -> list[str]:
    from collections import Counter

    from apps.ai_engine.ml.data.preprocessing import content_tokens

    counter: Counter = Counter()
    for body in reviews:
        counter.update(content_tokens(body))
    return [token for token, _ in counter.most_common(top_n)]


def review_summary(product_id: int | str, refresh: bool = False) -> dict[str, Any]:
    """Return a cached, evidence-grounded review summary for a product."""
    from apps.catalog.models import Product
    from apps.reviews.models import Review, ReviewSummary

    product = Product.objects.get(pk=product_id)
    reviews = list(
        Review.objects.filter(product=product).values_list("rating", "body")
    )

    cached = getattr(product, "ai_summary", None)
    try:
        cached = ReviewSummary.objects.get(product=product)
    except ReviewSummary.DoesNotExist:
        cached = None

    needs_refresh = (
        refresh
        or cached is None
        or cached.evidence_count if False else (cached is not None and (len(reviews) != getattr(cached, "_evidence_count", len(reviews))))
    )
    # Simpler staleness rule: refresh when review count changed.
    if cached is not None:
        try:
            if int(getattr(cached, "evidence_count_cached", -1)) != len(reviews):
                needs_refresh = True
        except Exception:
            pass

    if not needs_refresh and cached is not None:
        return {
            "product_id": str(product.pk),
            "product_name": product.name,
            "summary": cached.summary,
            "sentiment_score": float(cached.sentiment_score or 0),
            "model_version": cached.model_version,
            "generated_at": cached.generated_at.isoformat() if cached.generated_at else None,
            "review_count": len(reviews),
            "cached": True,
        }

    if not reviews:
        summary_text = "No reviews yet for this product."
        positive_themes: list[str] = []
        negative_themes: list[str] = []
        sentiment_score = 0.0
    else:
        bodies = [body for _, body in reviews]
        ratings = [rating for rating, _ in reviews]
        avg = sum(ratings) / len(ratings)
        sentiment_score = round((avg - 3) / 2, 2)  # -1..1

        positive_bodies = [body for rating, body in reviews if rating >= 4]
        negative_bodies = [body for rating, body in reviews if rating <= 2]
        positive_themes = _themes(positive_bodies or bodies)
        negative_themes = _themes(negative_bodies)
        from apps.ai_engine.services.ml_service import summarize_reviews as ml_summarize

        overall = ml_summarize(bodies, max_sentences=3)
        summary_text = (
            f"Overall: {overall}\n"
            f"Positive themes: {', '.join(positive_themes) if positive_themes else 'none'}\n"
            f"Negative themes: {', '.join(negative_themes) if negative_themes else 'none'}"
        )

    if cached is None:
        cached = ReviewSummary(product=product)
    cached.summary = summary_text
    cached.sentiment_score = sentiment_score
    cached.model_version = "local-extractive-v1"
    try:
        cached.evidence_count_cached = len(reviews)
    except Exception:
        pass
    cached.save()

    return {
        "product_id": str(product.pk),
        "product_name": product.name,
        "summary": summary_text,
        "positive_themes": positive_themes if reviews else [],
        "negative_themes": negative_themes if reviews else [],
        "sentiment_score": sentiment_score,
        "model_version": cached.model_version,
        "generated_at": cached.generated_at.isoformat() if cached.generated_at else None,
        "review_count": len(reviews),
        "cached": False,
    }


# --------------------------------------------------------------------------- #
# Customer support RAG
# --------------------------------------------------------------------------- #
_SENSITIVE_KEYWORDS = {
    "password", "credit card", "card number", "cvv", "payment details",
    "social security", "ssn", "delete account", "close account",
}


def _support_corpus(user=None) -> list[tuple[str, str, str]]:
    """Build (id, title, text) retrieval chunks. Order data is user-scoped."""
    chunks: list[tuple[str, str, str]] = []
    # Policies.
    chunks.append(("policy-shipping", "Shipping policy", "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days. Free shipping on orders over $50."))
    chunks.append(("policy-returns", "Returns policy", "Returns are accepted within 30 days of delivery. Items must be unused and in original packaging. Refunds are issued to the original payment method."))
    chunks.append(("policy-orders", "Order tracking", "You can track orders from your account order history. Provide an order number to look up its status."))
    chunks.append(("policy-privacy", "Privacy policy", "We never share payment details. We only store what is needed to fulfill your order."))

    # Product catalog snippets.
    for product in Product.objects.filter(is_active=True).select_related("category", "brand")[:200]:
        price = product.current_price
        stock = "in stock" if product.stock_quantity > 0 else "out of stock"
        specs = json.dumps(product.specifications or {})
        text = f"{product.name}. {product.description or ''} Category: {getattr(product.category, 'name', '')}. Brand: {getattr(product.brand, 'name', '')}. Price ${price}. {stock}. Specifications: {specs}."
        chunks.append((f"product-{product.pk}", product.name, text))

    # User-scoped order data only.
    if user is not None and getattr(user, "is_authenticated", False):
        try:
            from apps.orders.models import Order

            for order in Order.objects.filter(user=user).order_by("-created_at")[:10]:
                chunks.append(
                    (
                        f"order-{order.pk}",
                        f"Order {str(order.pk)[:8]}",
                        f"Order {order.pk} status is {order.status}. Total ${order.total}. Created {order.created_at}.",
                    )
                )
        except Exception:
            pass
    return chunks


def support_answer(query: str, user=None) -> dict[str, Any]:
    """Answer a support question using retrieval-augmented local search."""
    lowered = (query or "").lower()
    if any(keyword in lowered for keyword in _SENSITIVE_KEYWORDS):
        return {
            "answer": "I can't help with sensitive account or payment details. Please contact human support for assistance.",
            "sources": [],
            "escalated": True,
        }

    chunks = _support_corpus(user)
    retrieval_query = query or ""
    lowered = retrieval_query.lower()
    if "return" in lowered or "refund" in lowered:
        retrieval_query = "returns policy " + retrieval_query
    elif "ship" in lowered or "delivery" in lowered:
        retrieval_query = "shipping policy " + retrieval_query
    elif "order" in lowered or "track" in lowered or "status" in lowered:
        retrieval_query = "order tracking " + retrieval_query

    # Build a live TF-IDF index over the (permission-scoped) corpus.
    try:
        from apps.ai_engine.ml.algorithms.text_embedding import TfidfEmbeddingModel

        ids = [chunk[0] for chunk in chunks]
        docs = [chunk[2] for chunk in chunks]
        model = TfidfEmbeddingModel().fit(ids, docs)
        hits = model.search(retrieval_query or "", k=5)
    except Exception:
        hits = []

    if not hits or (hits and hits[0][1] < 0.05):
        return {
            "answer": "I’m not confident I can answer that accurately. I’m escalating this to a human support agent who can help.",
            "sources": [],
            "escalated": True,
        }

    top_chunks = [next(c for c in chunks if c[0] == hit_id) for hit_id, _ in hits if any(c[0] == hit_id for c in chunks)]
    sources = [{"id": c[0], "title": c[1]} for c in top_chunks]

    # Optional local LLM synthesis (never required).
    use_llm = bool(getattr(settings, "AI_LLM_ENABLED", False))
    if use_llm:
        try:
            from apps.ai_engine.services.ml_service import summarize_reviews as _unused  # noqa
        except Exception:
            use_llm = False

    context = "\n".join(f"- {c[2]}" for c in top_chunks)
    answer = (
        "Based on our records and policies:\n"
        + context
        + "\n\nLet me know if you need more help."
    )

    # Order-specific direct lookup to guarantee correctness/permissions.
    order_reference = None
    try:
        import re, uuid

        match = re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            query.lower(),
        )
        if match and user is not None and getattr(user, "is_authenticated", False):
            from apps.orders.models import Order

            candidate = Order.objects.filter(pk=uuid.UUID(match.group(0)), user=user).first()
            if candidate is not None:
                order_reference = f"Order {str(candidate.pk)[:8]} is {candidate.status}."
    except Exception:
        order_reference = None
    if order_reference:
        answer = order_reference + "\n\n" + answer

    return {"answer": answer, "sources": sources, "escalated": False}

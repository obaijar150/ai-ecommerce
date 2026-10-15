"""
Django-facing facade over the isolated ``ai_engine.ml`` package.

The views never import the ML package directly. They call these small,
defensively-written helpers, which:

* load the newest trained artifacts,
* fall back to deterministic behaviour when no artifact exists, and
* convert item ids back into ``Product`` objects for templates/APIs.

Every method swallows infrastructure errors and degrades to a safe result, so a
missing model or a heavy optional dependency can never break a request.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

from apps.catalog.models import Product

from ..ml.inference.assistant import ProductAssistant
from ..ml.inference.recommender import RecommenderInference
from ..ml.inference.semantic_search import SemanticSearchService

if TYPE_CHECKING:  # pragma: no cover - typing only
    from django.contrib.auth.models import AbstractBaseUser

    _User = AbstractBaseUser

logger = logging.getLogger(__name__)


def _item_features() -> dict[str, dict]:
    """Load catalog features for the ML package (lazy import avoids cycles)."""
    from ..ml.data.django_source import load_item_features

    return load_item_features()


def _activity_interactions() -> list[dict]:
    """Load first-party interaction rows used for the fallback model."""
    from ..ml.data.django_source import load_interactions_from_activity

    return load_interactions_from_activity()


def _user_seen_product_ids(user: "_User") -> set[str]:
    """Return product ids the user has already interacted with or ordered."""
    from ..models import UserActivityLog

    seen = set(
        UserActivityLog.objects.filter(user=user, product__isnull=False)
        .values_list("product_id", flat=True)
        .distinct()
    )
    try:
        from apps.orders.models import OrderItem

        seen.update(
            OrderItem.objects.filter(order__user=user)
            .values_list("product_id", flat=True)
            .distinct()
        )
    except Exception:  # pragma: no cover - orders app always present in practice
        pass
    return {str(product_id) for product_id in seen}


def recommend_products(user: "_User", limit: int = 10) -> list[Product]:
    """Return recommended ``Product`` objects for ``user``.

    Uses the newest trained recommender artifact when available, otherwise a
    deterministic popularity model built from first-party activity. Inactive or
    missing products are filtered out.

    Args:
        user: The authenticated user.
        limit: Maximum number of products to return.

    Returns:
        A list of active ``Product`` objects, best first. Empty on any failure.
    """
    scored, _algorithm = recommend_products_scored(user, limit)
    return [product for product, _score in scored]


def recommend_products_scored(
    user: "_User", limit: int = 10
) -> tuple[list[tuple[Product, float]], str]:
    """Return ``([(Product, score)], algorithm)`` for ``user``.

    The algorithm is the name reported by the active model
    (``"hybrid"``/``"popularity"``), which is recorded on cached recommendations
    so the provenance of a suggestion is auditable.

    Args:
        user: The authenticated user.
        limit: Maximum number of products to return.

    Returns:
        A ``(pairs, algorithm)`` tuple. ``pairs`` is empty and ``algorithm`` is
        ``"popularity"`` on any failure.
    """
    try:
        engine = RecommenderInference(
            fallback_interactions=_activity_interactions(),
            fallback_item_features=_item_features(),
        )
        user_id = f"u{user.pk}"
        item_ids = engine.recommend(
            user_id, k=limit, exclude_seen=_user_seen_product_ids(user)
        )
        if not item_ids:
            return [], engine.algorithm
        scores = engine.score(user_id, item_ids)
        algorithm = engine.algorithm
    except Exception:
        logger.exception("Recommendation inference failed; returning no results.")
        return [], "popularity"

    products = Product.objects.filter(pk__in=item_ids, is_active=True).select_related(
        "category"
    )
    by_id = {str(product.pk): product for product in products}
    pairs = [
        (by_id[item_id], float(scores[index]))
        for index, item_id in enumerate(item_ids)
        if item_id in by_id
    ]
    return pairs, algorithm


def semantic_search(
    query: str, limit: int = 10
) -> list[tuple[Product, float]]:
    """Return ``(Product, score)`` pairs most similar to ``query``.

    Fits a live TF-IDF index over the catalog when no offline index artifact
    exists, so the feature works out of the box. Results are ordered by score.

    Args:
        query: Free-text search query.
        limit: Maximum number of results.

    Returns:
        A list of ``(Product, score)`` tuples. Empty when nothing matches or on
        failure.
    """
    query = (query or "").strip()
    if not query:
        return []

    # Tolerate simple inflection (headphone <-> headphones) so a user phrasing
    # in the singular still matches a catalog written in the plural.
    candidates = [query]
    if query.endswith("s") and len(query) > 3:
        candidates.append(query[:-1])
    else:
        candidates.append(query + "s")

    try:
        features = _item_features()
        if not features:
            return []
        item_ids = sorted(features)
        documents = [features[item_id]["text"] for item_id in item_ids]
        by_id_candidates = set(features)

        hits = []
        for candidate in candidates:
            # Prefer a persisted (possibly trained/offline) index when available.
            service = SemanticSearchService(
                artifact_name="embedding_index",
                live_item_ids=item_ids,
                live_documents=documents,
            )
            hits = service.search(candidate, k=limit)

            # Guard against stale persisted indexes that no longer match the live
            # catalog: if none of the hits resolve to a current product, refit a
            # live TF-IDF index over the current catalog and search again.
            if not any(item_id in by_id_candidates for item_id, _ in hits):
                live_service = SemanticSearchService(
                    artifact_name="embedding_index__live_fallback",
                    live_item_ids=item_ids,
                    live_documents=documents,
                )
                hits = live_service.search(candidate, k=limit)

            if hits:
                break
    except Exception:
        logger.exception("Semantic search failed; returning no results.")
        return []

    if not hits:
        return []

    hit_ids = [item_id for item_id, _ in hits]
    products = Product.objects.filter(pk__in=hit_ids, is_active=True)
    by_id = {str(product.pk): product for product in products}
    return [
        (by_id[item_id], score) for item_id, score in hits if item_id in by_id
    ]


def summarize_reviews(products_reviews: list[str], max_sentences: int = 3) -> str:
    """Summarize a list of review bodies with graceful fallback.

    Uses the optional local LLM only when enabled in settings; otherwise the
    deterministic extractive summarizer is used.

    Args:
        products_reviews: Review body strings.
        max_sentences: Maximum sentences in the summary.

    Returns:
        A summary string (possibly empty for empty input).
    """
    backend = getattr(settings, "AI_LLM_BACKEND", "extractive")
    enabled = getattr(settings, "AI_LLM_ENABLED", False)
    assistant = ProductAssistant(
        summary_backend=backend if enabled else "extractive",
        ollama_model=getattr(settings, "OLLAMA_MODEL", "qwen2.5:0.5b"),
        base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
        enable_llm=enabled,
    )
    try:
        return assistant.summarize_reviews(products_reviews, max_sentences=max_sentences)
    except Exception:
        logger.exception("Review summarization failed; returning empty summary.")
        return ""

"""AI-powered semantic product search with hard filters and ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db.models import Q

from apps.catalog.models import Product

from .constraints import extract_constraints
from .ml_service import _item_features, semantic_search as ml_semantic_search
from apps.ai_engine.text.normalizer import normalize


@dataclass
class AISearchResult:
    product: Product
    score: float
    reasons: list[str]


def ai_search(query: str, limit: int = 24) -> tuple[dict[str, Any], list[AISearchResult]]:
    """Run constraint-aware semantic product search.

    Args:
        query: Natural-language request from the user.
        limit: Maximum number of products to return.

    Returns:
        A ``(constraints, results)`` tuple where ``results`` is a list of
        :class:`AISearchResult` objects ordered by descending relevance.
    """
    constraints = extract_constraints(query)
    normalized = normalize(query)

    queryset = Product.objects.filter(is_active=True)
    # Hard price filters.
    if constraints["budget_max"] is not None:
        queryset = queryset.with_effective_price().filter(
            effective_price__lte=constraints["budget_max"]
        )
    if constraints["budget_min"] is not None:
        queryset = queryset.with_effective_price().filter(
            effective_price__gte=constraints["budget_min"]
        )
    # Availability filter.
    if constraints["availability_required"]:
        queryset = queryset.filter(stock_quantity__gt=0)
    # Category filter (best-effort name match).
    if constraints["category"]:
        queryset = queryset.filter(
            Q(category__slug__icontains=constraints["category"])
            | Q(category__name__icontains=constraints["category"])
        )

    candidates = list(queryset.select_related("category", "brand")[:limit * 4 or 100])
    if not candidates:
        return constraints, []

    # Semantic ranking over the filtered candidate set (live TF-IDF, no
    # pretrained/stale artifacts so results always reflect current stock).
    candidate_text = {
        str(product.pk): (
            f"{product.name} {product.description or ''} "
            f"{getattr(product.category, 'name', '')} "
            f"{getattr(product.brand, 'name', '')} "
            f"{product.specifications or ''}"
        )
        for product in candidates
    }
    try:
        from apps.ai_engine.ml.algorithms.text_embedding import TfidfEmbeddingModel

        model = TfidfEmbeddingModel().fit(
            list(candidate_text.keys()), list(candidate_text.values())
        )
        hits = model.search(normalized or query, k=min(limit, len(candidates)))
    except Exception:
        hits = [(str(p.pk), 0.0) for p in candidates[:limit]]

    candidate_by_id = {str(product.pk): product for product in candidates}
    scored: list[AISearchResult] = []
    for product_id, score in hits:
        product = candidate_by_id.get(product_id)
        if not product:
            continue
        scored.append(AISearchResult(product=product, score=float(score), reasons=_reasons(product, constraints)))

    # If semantic matching returned nothing (e.g. empty vocab overlap), fall
    # back to popularity order over the already-filtered candidates.
    if not scored:
        scored = [
            AISearchResult(product=product, score=0.0, reasons=_reasons(product, constraints))
            for product in candidates[:limit]
        ]

    return constraints, scored[:limit]


def _reasons(product: Product, constraints: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if constraints["category"]:
        reasons.append(f"category matches '{constraints['category']}'")
    if constraints["budget_max"] is not None:
        price = float(product.current_price if hasattr(product, "current_price") else product.price)
        if price <= constraints["budget_max"]:
            reasons.append(f"price ${price:g} within budget ${constraints['budget_max']:g}")
    if constraints["availability_required"] and getattr(product, "stock_quantity", 0) > 0:
        reasons.append("in stock")
    if constraints["intended_use"]:
        reasons.append(f"suitable for {constraints['intended_use']}")
    if not reasons:
        reasons.append(" matches the request text")
    return reasons

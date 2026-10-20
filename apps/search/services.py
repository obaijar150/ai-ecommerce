"""
Search services: PostgreSQL full-text search with ranking, fuzzy correction,
and reciprocal-rank fusion (RRF).

Falls back to a portable SQLite-friendly implementation when PostgreSQL is not
available, keeping the same public API.
"""

from typing import Optional

from django.db import connection
from django.db.models import Case, IntegerField, Value, When

from apps.catalog.models import Product


def _is_postgres() -> bool:
    """Return whether the active database engine is PostgreSQL."""
    return connection.vendor == "postgresql"


def _corrected_query(query: str) -> str:
    """Return a spell-corrected version of ``query`` when possible."""
    try:
        from apps.ai_engine.text.spell_corrector import default_corrector

        corrected = default_corrector().correct_text(query)
        return corrected or query
    except Exception:
        return query


class SearchService:
    """Service for performing full-text product searches."""

    @staticmethod
    def search_products(query: str, limit: Optional[int] = None):
        """Search products using Postgres FTS + trigram (RRF) or portable fallback."""
        if not query or not query.strip():
            return Product.objects.none()

        corrected = _corrected_query(query)

        if not _is_postgres():
            # Portable fallback for dev/test (SQLite).
            qs = Product.objects.filter(is_active=True).search(corrected)
            if limit:
                qs = qs[:limit]
            return qs

        # Postgres path
        from django.contrib.postgres.search import (
            SearchQuery,
            SearchRank,
            SearchVector,
            TrigramSimilarity,
        )

        search_vector = (
            SearchVector("name", weight="A")
            + SearchVector("description", weight="B")
            + SearchVector("sku", weight="B")
            + SearchVector("brand__name", weight="C")
            + SearchVector("category__name", weight="C")
        )
        search_query = SearchQuery(corrected, config="english")

        fts_qs = (
            Product.objects.filter(is_active=True)
            .annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gte=0.01)
            .order_by("-rank")[:50]
        )
        trigram_qs = (
            Product.objects.filter(is_active=True)
            .annotate(
                similarity=TrigramSimilarity("name", corrected)
                + TrigramSimilarity("description", corrected)
                + TrigramSimilarity("brand__name", corrected)
            )
            .filter(similarity__gt=0.1)
            .order_by("-similarity")[:50]
        )

        rrf_constant = 60
        scores: dict[int, float] = {}
        ordered_ids: list[int] = []
        for rank, product in enumerate(fts_qs, start=1):
            scores[product.pk] = scores.get(product.pk, 0.0) + 1.0 / (rrf_constant + rank)
            if product.pk not in ordered_ids:
                ordered_ids.append(product.pk)
        for rank, product in enumerate(trigram_qs, start=1):
            scores[product.pk] = scores.get(product.pk, 0.0) + 1.0 / (rrf_constant + rank)
            if product.pk not in ordered_ids:
                ordered_ids.append(product.pk)

        fused = sorted(ordered_ids, key=lambda pk: scores[pk], reverse=True)
        if limit:
            fused = fused[:limit]

        if not fused:
            return Product.objects.none()

        preserved_order = Case(
            *[When(pk=pk, then=Value(index)) for index, pk in enumerate(fused)],
            default=Value(len(fused)),
            output_field=IntegerField(),
        )
        return (
            Product.objects.filter(pk__in=fused, is_active=True)
            .annotate(_rrf_order=preserved_order)
            .order_by("_rrf_order")
        )

    @staticmethod
    def get_search_suggestions(query: str, limit: int = 5):
        """Get product name suggestions for autocomplete."""
        if not query or len(query) < 2:
            return Product.objects.none()

        corrected = _corrected_query(query)
        qs = Product.objects.filter(is_active=True, name__icontains=corrected)
        if not qs.exists():
            qs = Product.objects.filter(is_active=True, name__icontains=query)
        return qs.values_list("name", flat=True)[:limit]

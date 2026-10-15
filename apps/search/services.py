"""
Search services: PostgreSQL full-text search with ranking.
"""

from typing import Optional

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

from apps.catalog.models import Product


class SearchService:
    """Service for performing full-text product searches."""

    @staticmethod
    def search_products(
        query: str, limit: Optional[int] = None
    ):
        """
        Search products using PostgreSQL full-text search.

        Args:
            query: Search string from user
            limit: Maximum results to return

        Returns:
            QuerySet of Product objects ordered by relevance
        """
        if not query or not query.strip():
            return Product.objects.none()

        search_vector = (
            SearchVector("name", weight="A")
            + SearchVector("description", weight="B")
            + SearchVector("category__name", weight="C")
        )
        search_query = SearchQuery(query, config="english")

        results = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gte=0.01)
            .order_by("-rank")
        )

        if limit:
            results = results[:limit]

        return results

    @staticmethod
    def get_search_suggestions(query: str, limit: int = 5):
        """Get product name suggestions for autocomplete."""
        if not query or len(query) < 2:
            return Product.objects.none()

        return Product.objects.filter(
            is_active=True, name__icontains=query
        ).values_list("name", flat=True)[:limit]

"""
Search views: full-text product search with PostgreSQL FTS.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.shortcuts import render
from django.views.generic import ListView

from apps.catalog.models import Product

from .models import SearchQueryLog


class ProductSearchView(ListView):
    """Product search using PostgreSQL Full-Text Search."""

    model = Product
    template_name = "search/search_results.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        if not query:
            return Product.objects.none()

        # PostgreSQL full-text search with ranking
        search_vector = SearchVector("name", weight="A") + SearchVector(
            "description", weight="B"
        )
        search_query = SearchQuery(query, config="english")

        results = (
            Product.objects.filter(is_active=True)
            .annotate(
                rank=SearchRank(search_vector, search_query),
                search=search_vector,
            )
            .filter(search=search_query)
            .order_by("-rank")
        )

        # Log the search query
        self._log_search(query, results.count())

        return results

    def _log_search(self, query: str, results_count: int) -> None:
        """Log search query for analytics."""
        SearchQueryLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            session_key=self.request.session.session_key,
            query=query,
            results_count=results_count,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context

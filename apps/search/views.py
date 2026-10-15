"""
Search views: product search.

Uses PostgreSQL full-text search when the active backend supports it,
otherwise falls back to portable keyword matching so development and tests
on SQLite behave consistently.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.views.generic import ListView

from apps.catalog.models import Product

from .models import SearchQueryLog


def _supports_full_text() -> bool:
    """Return True when the active database backend supports Postgres FTS."""
    return connection.vendor == "postgresql"


class ProductSearchView(ListView):
    """Product search with keyword matching and optional Postgres FTS ranking."""

    model = Product
    template_name = "search/search_results.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        if not query:
            self._result_count = 0
            return Product.objects.none()

        if _supports_full_text():
            results = self._full_text_search(query)
        else:
            results = (
                Product.objects.active()
                .select_related("category", "brand")
                .prefetch_related("images")
                .search(query)
                .order_by("-view_count", "-created_at")
            )

        self._result_count = results.count()
        self._log_search(query, self._result_count)
        return results

    def _full_text_search(self, query: str):
        """Run a ranked PostgreSQL full-text search."""
        search_vector = SearchVector("name", weight="A") + SearchVector(
            "description", weight="B"
        )
        search_query = SearchQuery(query, config="english")
        return (
            Product.objects.active()
            .annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gt=0)
            .order_by("-rank")
        )

    def _log_search(self, query: str, results_count: int) -> None:
        """Log the search query for analytics."""
        session = self.request.session
        if not session.session_key:
            session.save()
        SearchQueryLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            session_key=session.session_key,
            query=query,
            results_count=results_count,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        context["total_count"] = getattr(self, "_result_count", 0)
        return context

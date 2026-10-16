"""
Catalog views: homepage, product listing (filter/sort/search/paginate),
product detail, and category pages.
"""

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from .models import Brand, Category, Product, ProductImage


# Valid sort keys mapped to ORM order_by expressions. ``effective_price`` is
# supplied by ProductQuerySet.with_effective_price().
VALID_SORT_FIELDS = {
    "newest": "-created_at",
    "price": "effective_price",
    "-price": "-effective_price",
    "name": "name",
    "-name": "-name",
    "rating": "-average_rating",
    "popular": "-view_count",
}

PAGE_SIZE = 12


def _base_product_queryset():
    """Return the standard annotated/related-loaded product queryset."""
    return (
        Product.objects.active()
        .with_effective_price()
        .select_related("category", "brand")
        .prefetch_related("images", "tags")
    )


class HomePageView(ListView):
    """Homepage with featured and recent products."""

    model = Product
    template_name = "catalog/home.html"
    context_object_name = "products"

    def get_queryset(self):
        return (
            _base_product_queryset()
            .filter(is_featured=True)
            .order_by("-created_at")[:8]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True, parent=None)
        context["recent_products"] = _base_product_queryset().order_by("-created_at")[:8]
        context["featured_brands"] = Brand.objects.filter(is_active=True)[:6]
        return context


def filter_products(request):
    """Build the filtered/sorted product queryset from request GET params.

    Kept as a standalone function so both the list view and the category
    detail view share identical filtering behaviour.

    Args:
        request: The current HTTP request.

    Returns:
        A tuple of (queryset, sort_key).
    """
    queryset = _base_product_queryset()

    # Category filter — include products in child (sub)categories too.
    category_slug = request.GET.get("category", "").strip()
    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()
        if category:
            category_ids = [c.id for c in category.get_descendants(include_self=True)]
            queryset = queryset.filter(category_id__in=category_ids)

    # Brand filter.
    brand_slug = request.GET.get("brand", "").strip()
    if brand_slug:
        queryset = queryset.filter(brand__slug=brand_slug)

    # Tag filter.
    tag_slug = request.GET.get("tag", "").strip()
    if tag_slug:
        queryset = queryset.filter(tags__slug=tag_slug)

    # Keyword search.
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.search(query)

    # Price range (database-level via the effective_price annotation).
    min_price = request.GET.get("min_price", "").strip()
    if min_price:
        try:
            queryset = queryset.filter(effective_price__gte=float(min_price))
        except ValueError:
            pass

    max_price = request.GET.get("max_price", "").strip()
    if max_price:
        try:
            queryset = queryset.filter(effective_price__lte=float(max_price))
        except ValueError:
            pass

    # In-stock only.
    if request.GET.get("in_stock"):
        queryset = queryset.filter(stock_quantity__gt=0)

    # Sorting.
    sort_key = request.GET.get("sort", "newest")
    queryset = queryset.order_by(VALID_SORT_FIELDS.get(sort_key, "-created_at"))

    return queryset, sort_key


class ProductListView(ListView):
    """Product listing with filtering, sorting, and pagination."""

    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        queryset, self._sort_key = filter_products(self.request)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True, parent=None)
        context["brands"] = Brand.objects.filter(is_active=True)
        context["active_sort"] = getattr(self, "_sort_key", "newest")
        context["query"] = self.request.GET.get("q", "").strip()
        context["total_count"] = context["paginator"].count if context.get("paginator") else len(context["products"])
        context["query_params"] = self._query_params_excluding_page()
        return context

    def _query_params_excluding_page(self) -> str:
        """Return the GET query string without the ``page`` parameter."""
        params = self.request.GET.copy()
        params.pop("page", None)
        return params.urlencode()


class CategoryDetailView(ListView):
    """Products within a single category (and its subcategories)."""

    model = Product
    template_name = "catalog/category_detail.html"
    context_object_name = "products"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, slug=self.kwargs["slug"], is_active=True
        )
        category_ids = [c.id for c in self.category.get_descendants(include_self=True)]
        queryset, self._sort_key = filter_products(self.request)
        return queryset.filter(category_id__in=category_ids)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        context["subcategories"] = self.category.children.filter(is_active=True)
        context["brands"] = Brand.objects.filter(is_active=True)
        context["active_sort"] = getattr(self, "_sort_key", "newest")
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_params"] = params.urlencode()
        return context


class ProductDetailView(DetailView):
    """Single product page with image gallery, specs, and reviews."""

    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Product.objects.active()
            .with_effective_price()
            .select_related("category", "brand")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.order_by("-is_primary", "sort_order")),
                "tags",
            )
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Atomic-ish increment; acceptable for a view counter.
        type(obj).objects.filter(pk=obj.pk).update(view_count=obj.view_count + 1)
        obj.view_count += 1
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context["images"] = product.images.all()
        context["primary_image"] = product.primary_image
        context["specifications"] = product.specifications or {}
        context["reviews"] = product.reviews.select_related("user")[:10]

        # AI-powered review summary and recommendations (graceful fallback).
        try:
            from apps.ai_engine.services.ai_integration import review_summary, explained_recommendations

            context["ai_review_summary"] = review_summary(product.pk)
        except Exception:
            context["ai_review_summary"] = None
        try:
            from apps.ai_engine.services.ai_integration import explained_recommendations

            recommendations = explained_recommendations(self.request.user, limit=4)
            context["ai_recommendations"] = [
                item for item in recommendations if item["product_id"] != str(product.pk)
            ][:4]
        except Exception:
            context["ai_recommendations"] = []

        if product.category:
            context["related_products"] = (
                _base_product_queryset()
                .filter(category=product.category)
                .exclude(pk=product.pk)[:4]
            )
        if product.brand:
            context["brand_products"] = (
                _base_product_queryset()
                .filter(brand=product.brand)
                .exclude(pk=product.pk)[:4]
            )
        return context


def page_not_found(request, exception=None):
    """Custom 404 handler."""
    return render(request, "404.html", status=404)


def server_error(request):
    """Custom 500 handler."""
    return render(request, "500.html", status=500)

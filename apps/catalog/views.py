"""
Catalog views: product listing, detail, category pages.
"""

from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from .models import Category, Product


class HomePageView(ListView):
    """Homepage with featured and recent products."""

    model = Product
    template_name = "catalog/home.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.filter(is_active=True, is_featured=True)[:8]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True, parent=None)
        context["recent_products"] = Product.objects.filter(is_active=True).order_by(
            "-created_at"
        )[:8]
        return context


class ProductListView(ListView):
    """Product listing with filtering by category."""

    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True, parent=None)
        return context


class ProductDetailView(DetailView):
    """Single product page with images, reviews, and recommendations."""

    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related(
            "images", "tags"
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        obj.view_count += 1
        obj.save(update_fields=["view_count"])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context["primary_image"] = product.images.filter(is_primary=True).first()
        context["reviews"] = product.reviews.select_related("user").all()[:10]
        return context


def page_not_found(request, exception=None):
    """Custom 404 handler."""
    return render(request, "404.html", status=404)


def server_error(request):
    """Custom 500 handler."""
    return render(request, "500.html", status=500)

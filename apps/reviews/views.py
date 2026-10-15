"""
Reviews views: create, list, mark helpful.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from django.db import models

from apps.catalog.models import Product

from .forms import ReviewForm
from .models import Review


@login_required
def review_create(request, product_slug: str):
    """Create a product review."""
    product = get_object_or_404(Product, slug=product_slug, is_active=True)

    # Check if user already reviewed this product
    if Review.objects.filter(product=product, user=request.user).exists():
        return redirect("catalog:product_detail", slug=product.slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            # Check for verified purchase
            review.is_verified_purchase = product.orders.filter(
                user=request.user
            ).exists()
            review.save()

            # Update product rating aggregates
            product.average_rating = product.reviews.aggregate(
                avg_rating=models.Avg("rating")
            )["avg_rating"] or 0
            product.review_count = product.reviews.count()
            product.save(update_fields=["average_rating", "review_count"])

            return redirect("catalog:product_detail", slug=product.slug)
    else:
        form = ReviewForm()

    context = {"form": form, "product": product}
    return render(request, "reviews/review_form.html", context)


class ReviewListView(ListView):
    """List all reviews for a product."""

    model = Review
    template_name = "reviews/review_list.html"
    context_object_name = "reviews"
    paginate_by = 10

    def get_queryset(self):
        product = get_object_or_404(Product, slug=self.kwargs["product_slug"])
        return Review.objects.filter(product=product).select_related("user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = get_object_or_404(
            Product, slug=self.kwargs["product_slug"]
        )
        return context


@login_required
def mark_helpful(request, review_id: int):
    """Mark a review as helpful (AJAX endpoint)."""
    review = get_object_or_404(Review, id=review_id)
    review.helpful_count += 1
    review.save(update_fields=["helpful_count"])
    return JsonResponse({"helpful_count": review.helpful_count})

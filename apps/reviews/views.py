"""
Reviews views: create, list, and mark helpful.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from apps.catalog.models import Product
from apps.orders.models import OrderItem

from .forms import ReviewForm
from .models import Review


@login_required
def review_create(request, product_slug: str):
    """Create a product review for the given product.

    Prevents duplicate reviews (one per user per product) and recomputes the
    product's rating aggregates after a successful save.
    """
    product = get_object_or_404(Product, slug=product_slug, is_active=True)

    if Review.objects.filter(product=product, user=request.user).exists():
        messages.info(request, "You have already reviewed this product.")
        return redirect("catalog:product_detail", slug=product.slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.is_verified_purchase = OrderItem.objects.filter(
                order__user=request.user, product=product
            ).exists()
            review.save()
            product.refresh_rating()
            messages.success(request, "Thanks! Your review has been posted.")
            return redirect("catalog:product_detail", slug=product.slug)
    else:
        form = ReviewForm()

    return render(request, "reviews/review_form.html", {"form": form, "product": product})


class ReviewListView(ListView):
    """List all reviews for a product, paginated."""

    model = Review
    template_name = "reviews/review_list.html"
    context_object_name = "reviews"
    paginate_by = 10

    def get_queryset(self):
        self.product = get_object_or_404(Product, slug=self.kwargs["product_slug"])
        return Review.objects.filter(product=self.product).select_related("user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        return context


@login_required
def mark_helpful(request, review_id: int):
    """Mark a review as helpful (AJAX POST endpoint)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    review = get_object_or_404(Review, id=review_id)
    Review.objects.filter(pk=review.pk).update(helpful_count=review.helpful_count + 1)
    review.helpful_count += 1
    return JsonResponse({"helpful_count": review.helpful_count})

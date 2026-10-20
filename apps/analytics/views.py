"""
Analytics views: admin dashboard with sales insights and staff-only management.
"""

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.validators import FileExtensionValidator
from django import forms
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import (
    CreateView,
    ListView,
    TemplateView,
    UpdateView,
)

from datetime import timedelta
from functools import wraps

from apps.catalog.forms import CategoryForm, ProductForm
from apps.catalog.models import Category, Product, ProductImage
from apps.catalog.validators import (
    ALLOWED_IMAGE_EXTENSIONS,
    validate_image_content_type,
    validate_image_size,
)
from apps.orders.models import Order
from apps.reviews.models import Review
from apps.ai_engine.models import UserActivityLog


def staff_required(view_func):
    """Allow only staff; redirect anonymous users to the login page."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff access only.")
        return view_func(request, *args, **kwargs)

    return _wrapped


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict views to authenticated staff users."""

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return HttpResponseForbidden("Staff access only.")


class ProductAdminForm(ProductForm):
    """Staff product form that also accepts a primary image upload.

    Extends the shared :class:`apps.catalog.forms.ProductForm` (so all SKU,
    price and specification validation applies) with an optional image field.
    Uploaded images are stored as :class:`ProductImage` rows, matching how the
    rest of the catalogue handles product media.
    """

    image = forms.ImageField(
        required=False,
        label="Primary image",
        help_text="JPEG, PNG or WebP. Validated for size and real content type.",
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
            validate_image_content_type,
        ],
    )
    image_alt_text = forms.CharField(
        required=False,
        max_length=200,
        label="Image alt text",
        help_text="Describes the image for screen readers and search engines.",
    )


def _store_primary_image(product: Product, image, alt_text: str = "") -> None:
    """Persist an uploaded image as ``product``'s new primary image."""
    product.images.filter(is_primary=True).update(is_primary=False)
    ProductImage.objects.create(
        product=product,
        image=image,
        alt_text=alt_text or product.name,
        is_primary=True,
    )


class CategoryAdminForm(CategoryForm):
    """Staff category form with a sensible ``sort_order`` default."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sort_order"].required = False

    def clean_sort_order(self):
        return self.cleaned_data.get("sort_order") or 0


@staff_required
def dashboard(request):
    """Admin analytics dashboard."""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)

    total_revenue = Order.objects.filter(
        status__in=["paid", "shipped", "delivered"]
    ).aggregate(total=Sum("total"))["total"] or 0
    monthly_revenue = Order.objects.filter(
        status__in=["paid", "shipped", "delivered"],
        created_at__date__gte=thirty_days_ago,
    ).aggregate(total=Sum("total"))["total"] or 0
    weekly_orders = Order.objects.filter(
        created_at__date__gte=seven_days_ago
    ).count()

    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(
        is_active=True, stock_quantity__lte=10
    ).count()
    total_activities = UserActivityLog.objects.count()
    popular_products = Product.objects.filter(is_active=True).order_by(
        "-view_count"
    )[:5]
    recent_orders = Order.objects.select_related("user").order_by("-created_at")[:10]

    context = {
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "weekly_orders": weekly_orders,
        "total_products": total_products,
        "low_stock_products": low_stock_products,
        "total_activities": total_activities,
        "popular_products": popular_products,
        "recent_orders": recent_orders,
    }
    return render(request, "analytics/dashboard.html", context)


@staff_required
def sales_report(request):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_sales = (
        Order.objects.filter(
            status__in=["paid", "shipped", "delivered"],
            created_at__date__gte=thirty_days_ago,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total_sales=Sum("total"), order_count=Count("id"))
        .order_by("date")
    )
    return render(request, "analytics/sales_report.html", {"daily_sales": daily_sales})


class ProductManagementListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = "analytics/product_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        return Product.objects.select_related("category", "brand").order_by("-created_at")


class ProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductAdminForm
    template_name = "analytics/product_form.html"
    success_url = "/analytics/products/"

    def form_valid(self, form):
        response = super().form_valid(form)
        image = form.cleaned_data.get("image")
        if image:
            _store_primary_image(
                self.object, image, form.cleaned_data.get("image_alt_text", "")
            )
        messages.success(self.request, "Product created.")
        return response


class ProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductAdminForm
    template_name = "analytics/product_form.html"
    success_url = "/analytics/products/"

    def form_valid(self, form):
        response = super().form_valid(form)
        image = form.cleaned_data.get("image")
        if image:
            _store_primary_image(
                self.object, image, form.cleaned_data.get("image_alt_text", "")
            )
        messages.success(self.request, "Product updated.")
        return response


class CategoryManagementListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = "analytics/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.order_by("name")


class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryAdminForm
    template_name = "analytics/category_form.html"
    success_url = "/analytics/categories/"

    def form_valid(self, form):
        messages.success(self.request, "Category created.")
        return super().form_valid(form)


class StockUpdateView(StaffRequiredMixin, TemplateView):
    template_name = "analytics/stock_update.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["low_stock"] = Product.objects.filter(
            is_active=True, stock_quantity__lte=10
        ).order_by("stock_quantity")
        return context

    def post(self, request, *args, **kwargs):
        pk = request.POST.get("product_id")
        try:
            quantity = int(request.POST.get("quantity", "0"))
        except (TypeError, ValueError):
            quantity = None
        product = get_object_or_404(Product, pk=pk)
        if quantity is not None and quantity >= 0:
            product.stock_quantity = quantity
            product.save(update_fields=["stock_quantity"])
            messages.success(request, f"Stock updated for {product.name}.")
        return redirect("analytics:stock_update")


class OrderManagementListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = "analytics/order_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        queryset = Order.objects.select_related("user").order_by("-created_at")
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Order.Status.choices
        return context

    def post(self, request, *args, **kwargs):
        pk = request.POST.get("order_id")
        new_status = request.POST.get("status")
        order = get_object_or_404(Order, pk=pk)
        if new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"Order {order.id} updated.")
        return redirect(request.get_full_path())


class ReviewManagementListView(StaffRequiredMixin, ListView):
    model = Review
    template_name = "analytics/review_list.html"
    context_object_name = "reviews"
    paginate_by = 25

    def get_queryset(self):
        return Review.objects.select_related("product", "user").order_by("-created_at")

    def post(self, request, *args, **kwargs):
        pk = request.POST.get("review_id")
        if request.POST.get("action") == "delete":
            Review.objects.filter(pk=pk).delete()
            messages.success(request, "Review deleted.")
        return redirect("analytics:review_list")

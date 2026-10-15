"""
Django admin configuration for the catalog app.

Provides rich management screens for brands, categories (with subcategories),
products (with inline images and inventory), tags, and inventory itself.
"""

from django.contrib import admin
from django.utils.html import format_html

from .forms import BrandForm, CategoryForm, ProductForm, ProductImageForm
from .models import Brand, Category, Product, ProductImage, ProductInventory, Tag


class ProductImageInline(admin.TabularInline):
    """Inline editor for product images in the product admin page."""

    model = ProductImage
    extra = 1
    form = ProductImageForm
    readonly_fields = ["image_preview"]
    fields = ["image", "image_preview", "alt_text", "is_primary", "sort_order"]

    def image_preview(self, obj) -> str:
        """Display an image thumbnail in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 120px; '
                'border-radius: 4px;" />',
                obj.image.url,
            )
        return "No image"

    image_preview.short_description = "Preview"


class ProductInventoryInline(admin.StackedInline):
    """Inline editor for inventory in the product admin page."""

    model = ProductInventory
    extra = 0
    max_num = 1
    fields = ["quantity", "reserved_quantity", "reorder_level", "last_restocked"]
    readonly_fields = ["available_quantity_display", "needs_reorder_display"]

    def available_quantity_display(self, obj) -> int:
        return obj.available_quantity if obj.pk else 0

    def needs_reorder_display(self, obj) -> str:
        if not obj.pk:
            return "—"
        if obj.needs_reorder:
            return format_html(
                '<span style="color: #dc2626; font-weight: bold;">⚠ Reorder</span>'
            )
        return format_html('<span style="color: #16a34a;">OK</span>')

    available_quantity_display.short_description = "Available"
    needs_reorder_display.short_description = "Needs Reorder"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    form = BrandForm
    list_display = ["name", "slug", "product_count", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    list_per_page = 30

    @admin.display(description="Products")
    def product_count(self, obj) -> int:
        return obj.products.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = [
        "name",
        "slug",
        "parent",
        "product_count",
        "is_active",
        "sort_order",
    ]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ["parent"]
    ordering = ["sort_order", "name"]

    @admin.display(description="Products")
    def product_count(self, obj) -> str:
        count = obj.product_count
        if count > 0:
            return format_html(
                '<span style="font-weight: bold; color: #4f46e5;">{}</span>', count
            )
        return str(count)


class LowStockFilter(admin.SimpleListFilter):
    """Filter products by stock level."""

    title = "stock level"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [
            ("out", "Out of stock"),
            ("low", "Low stock"),
            ("in", "In stock"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "out":
            return queryset.filter(stock_quantity=0)
        if value == "low":
            return queryset.filter(stock_quantity__gt=0, stock_quantity__lte=10)
        if value == "in":
            return queryset.filter(stock_quantity__gt=10)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = [
        "name",
        "sku",
        "category",
        "brand",
        "price_display",
        "stock_status",
        "rating_display",
        "is_active",
        "is_featured",
    ]
    list_filter = [
        "is_active",
        "is_featured",
        "category",
        "brand",
        LowStockFilter,
        "created_at",
    ]
    search_fields = ["name", "sku", "description", "brand__name"]
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ["category", "brand"]
    inlines = [ProductImageInline, ProductInventoryInline]
    readonly_fields = ["average_rating", "review_count", "view_count"]
    save_on_top = True

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "slug", "sku", "category", "brand", "tags")},
        ),
        (
            "Pricing",
            {
                "fields": ("price", "sale_price"),
                "description": "Set sale_price for discounted items.",
            },
        ),
        (
            "Inventory",
            {"fields": ("stock_quantity", "low_stock_threshold", "weight_kg")},
        ),
        ("Details", {"fields": ("description", "specifications")}),
        ("Flags", {"fields": ("is_active", "is_featured")}),
        (
            "Metrics (read-only)",
            {"fields": ("average_rating", "review_count", "view_count")},
        ),
    )

    @admin.display(description="Price", ordering="price")
    def price_display(self, obj) -> str:
        if obj.sale_price:
            return format_html(
                '<span style="color: #dc2626; font-weight: bold;">${:}</span> '
                '<s style="color: #999;">${:}</s>',
                f"{obj.sale_price:.2f}",
                f"{obj.price:.2f}",
            )
        return f"${obj.price:.2f}"

    @admin.display(description="Stock", ordering="stock_quantity")
    def stock_status(self, obj) -> str:
        if obj.stock_quantity == 0:
            return format_html(
                '<span style="color: #dc2626; font-weight: bold;">Out of Stock</span>'
            )
        if obj.stock_quantity <= 10:
            return format_html(
                '<span style="color: #d97706;">Low ({})</span>', obj.stock_quantity
            )
        return format_html(
            '<span style="color: #16a34a;">In Stock ({})</span>', obj.stock_quantity
        )

    @admin.display(description="Rating", ordering="average_rating")
    def rating_display(self, obj) -> str:
        if obj.review_count > 0:
            full = int(obj.average_rating)
            stars = "★" * full + "☆" * (5 - full)
            return format_html(
                '<span style="color: #f59e0b;">{}</span> '
                '<span style="color: #999;">({}, {} reviews)</span>',
                stars,
                f"{obj.average_rating:.1f}",
                obj.review_count,
            )
        return "No reviews"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "product_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]

    @admin.display(description="Products")
    def product_count(self, obj) -> int:
        return obj.products.count()


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "image_preview", "is_primary", "sort_order"]
    list_filter = ["is_primary"]
    search_fields = ["product__name", "alt_text"]
    readonly_fields = ["image_preview"]

    @admin.display(description="Preview")
    def image_preview(self, obj) -> str:
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 60px; max-width: 90px; '
                'border-radius: 4px;" />',
                obj.image.url,
            )
        return "No image"


@admin.register(ProductInventory)
class ProductInventoryAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "quantity",
        "reserved_quantity",
        "available_quantity",
        "reorder_level",
        "needs_reorder",
    ]
    list_filter = ["product__category"]
    search_fields = ["product__name", "product__sku"]
    list_select_related = ["product"]

    @admin.display(description="Available", ordering="quantity")
    def available_quantity(self, obj) -> int:
        return obj.available_quantity

    @admin.display(description="Needs Reorder")
    def needs_reorder(self, obj) -> str:
        if obj.needs_reorder:
            return format_html(
                '<span style="color: #dc2626; font-weight: bold;">⚠ Reorder</span>'
            )
        return format_html('<span style="color: #16a34a;">OK</span>')

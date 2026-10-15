"""
Django admin configuration for catalog app.
"""

from django.contrib import admin

from .models import Category, Product, ProductImage, ProductInventory, Tag


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "is_active", "sort_order"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sku",
        "category",
        "price",
        "sale_price",
        "stock_quantity",
        "is_active",
        "is_featured",
        "average_rating",
    ]
    list_filter = ["is_active", "is_featured", "category"]
    search_fields = ["name", "sku", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


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
    list_filter = ["reorder_level"]

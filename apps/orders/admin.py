"""
Django admin configuration for orders app.
"""

from django.contrib import admin

from .models import CartItem, Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user__username", "tracking_number"]
    inlines = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["user", "session_key", "product", "quantity", "added_at"]

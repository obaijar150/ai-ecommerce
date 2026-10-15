"""
Django admin configuration for orders app.

The admin is the safest place for staff to inspect orders, payment records and
status history. Status-changing actions restore stock where appropriate and are
recorded in the audit trail.
"""

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import CartItem, Order, OrderItem, OrderStatusHistory, Payment
from .services import OrderService


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "product_name", "product_sku", "unit_price", "total_price"]
    can_delete = False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["status", "notes", "changed_by", "created_at"]
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = [
        "provider",
        "transaction_id",
        "amount",
        "status",
        "failure_reason",
        "confirmed_at",
        "created_at",
    ]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "short_id",
        "user",
        "status",
        "payment_badge",
        "total",
        "created_at",
    ]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["id", "user__username", "user__email", "tracking_number"]
    readonly_fields = [
        "id",
        "short_id",
        "subtotal",
        "tax",
        "shipping_cost",
        "total",
        "paid_at",
        "idempotency_key",
        "created_at",
        "updated_at",
    ]
    list_select_related = ["user"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, OrderStatusHistoryInline, PaymentInline]
    actions = ["mark_shipped", "mark_delivered", "cancel_and_restore"]

    @admin.display(description="Order")
    def short_id(self, obj: Order) -> str:
        return obj.short_id

    @admin.display(description="Payment")
    def payment_badge(self, obj: Order) -> str:
        payment = obj.latest_payment
        if payment is None:
            color = "#6b7280"  # gray
            label = "—"
        elif payment.succeeded:
            color = "#059669"  # green
            label = "Paid"
        elif payment.status == Payment.Status.FAILED:
            color = "#dc2626"  # red
            label = "Failed"
        else:
            color = "#d97706"  # amber
            label = "Pending"
        return format_html(
            '<strong style="color:{}">{}</strong>', color, label
        )

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        self._transition_selected(request, queryset, Order.Status.SHIPPED, "Shipped")

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        self._transition_selected(
            request, queryset, Order.Status.DELIVERED, "Delivered"
        )

    @admin.action(description="Cancel selected orders and restore stock")
    def cancel_and_restore(self, request, queryset):
        done = 0
        for order in queryset:
            try:
                OrderService.cancel_order(order, changed_by=request.user)
                done += 1
            except Exception as exc:  # noqa: BLE001 - report and continue
                self.message_user(
                    request, f"{order.short_id}: {exc}", level=messages.ERROR
                )
        if done:
            self.message_user(request, f"Cancelled {done} order(s).", messages.SUCCESS)

    def _transition_selected(self, request, queryset, status, label):
        done = 0
        for order in queryset:
            try:
                OrderService.transition(
                    order, status, label, changed_by=request.user
                )
                done += 1
            except Exception as exc:  # noqa: BLE001 - report and continue
                self.message_user(
                    request, f"{order.short_id}: {exc}", level=messages.ERROR
                )
        if done:
            self.message_user(request, f"{label} {done} order(s).", messages.SUCCESS)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "provider",
        "amount",
        "status",
        "transaction_id",
        "created_at",
    ]
    list_filter = ["status", "provider", "created_at"]
    search_fields = ["order__id", "transaction_id", "order__user__username"]
    readonly_fields = [
        "order",
        "provider",
        "transaction_id",
        "amount",
        "status",
        "failure_reason",
        "raw_response",
        "confirmed_at",
        "created_at",
        "updated_at",
    ]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["user", "session_key", "product", "quantity", "added_at"]
    list_filter = ["added_at"]
    search_fields = ["user__username", "product__name", "session_key"]
    list_select_related = ["user", "product"]

"""
Analytics views: admin dashboard with sales insights.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from apps.orders.models import Order
from apps.catalog.models import Product
from apps.ai_engine.models import UserActivityLog


@staff_member_required
def dashboard(request):
    """Admin analytics dashboard."""
    # Date ranges
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)

    # Sales metrics
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

    # Product metrics
    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(
        is_active=True, stock_quantity__lte=10
    ).count()

    # AI insights
    total_activities = UserActivityLog.objects.count()
    popular_products = Product.objects.filter(is_active=True).order_by(
        "-view_count"
    )[:5]

    # Recent orders
    recent_orders = Order.objects.select_related("user").order_by(
        "-created_at"
    )[:10]

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


@staff_member_required
def sales_report(request):
    """Detailed sales report."""
    # Daily sales for last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_sales = (
        Order.objects.filter(
            status__in=["paid", "shipped", "delivered"],
            created_at__date__gte=thirty_days_ago,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(
            total_sales=Sum("total"),
            order_count=Count("id"),
        )
        .order_by("date")
    )

    context = {"daily_sales": daily_sales}
    return render(request, "analytics/sales_report.html", context)

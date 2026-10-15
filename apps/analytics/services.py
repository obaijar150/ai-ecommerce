"""
Analytics services: sales aggregation, AI-powered insights.
"""

from typing import Dict

from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from apps.orders.models import Order
from apps.catalog.models import Product


class AnalyticsService:
    """Service for computing analytics metrics."""

    @staticmethod
    def get_sales_summary(days: int = 30) -> Dict:
        """Get sales summary for the last N days."""
        cutoff = timezone.now() - timedelta(days=days)

        orders = Order.objects.filter(
            status__in=["paid", "shipped", "delivered"],
            created_at__gte=cutoff,
        )

        return {
            "total_revenue": orders.aggregate(total=Sum("total"))["total"] or 0,
            "total_orders": orders.count(),
            "average_order_value": orders.aggregate(avg=Avg("total"))["avg"] or 0,
        }

    @staticmethod
    def get_inventory_alerts() -> Dict:
        """Get inventory alerts (low stock, out of stock)."""
        return {
            "low_stock": Product.objects.filter(
                is_active=True, stock_quantity__lte=10, stock_quantity__gt=0
            ).count(),
            "out_of_stock": Product.objects.filter(
                is_active=True, stock_quantity=0
            ).count(),
            "total_active": Product.objects.filter(is_active=True).count(),
        }

    @staticmethod
    def get_ai_insights() -> Dict:
        """Generate AI-powered business insights."""
        summary = AnalyticsService.get_sales_summary(30)
        inventory = AnalyticsService.get_inventory_alerts()

        insights = []

        if inventory["out_of_stock"] > 0:
            insights.append(
                f"You have {inventory['out_of_stock']} out-of-stock products. "
                "Consider restocking to avoid lost sales."
            )

        if inventory["low_stock"] > 5:
            insights.append(
                f"{inventory['low_stock']} products are running low. "
                "Review reorder levels."
            )

        if summary["total_orders"] > 0:
            avg = summary["average_order_value"]
            if avg < 30:
                insights.append(
                    f"Average order value (${avg:.2f}) is below $30. "
                    "Consider product bundles to increase AOV."
                )

        return {
            "insights": insights,
            "sales_summary": summary,
            "inventory": inventory,
        }

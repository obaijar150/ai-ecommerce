"""
Adapters that turn Django ORM data into the plain structures the ML package
expects. Imported lazily by the management commands so the core package stays
Django-free.
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from apps.catalog.models import Product


def load_item_features(products: QuerySet | None = None) -> dict[str, dict[str, Any]]:
    """Build ``{item_id: feature dict}`` from catalog products.

    Item ids are product primary keys as strings, matching how interactions are
    derived from activity and orders.

    Args:
        products: Optional pre-filtered queryset; defaults to active products.

    Returns:
        Mapping of product id to name/category/brand/price and a searchable
        ``text`` field.
    """
    queryset = products if products is not None else Product.objects.filter(is_active=True)
    features: dict[str, dict[str, Any]] = {}
    for product in queryset.select_related("category", "brand").iterator():
        category = getattr(product.category, "name", "") if product.category_id else ""
        brand = getattr(product.brand, "name", "") if product.brand_id else ""
        text_parts = [
            product.name or "",
            getattr(product, "description", "") or "",
            category,
            brand,
        ]
        features[str(product.pk)] = {
            "name": product.name,
            "category": category,
            "brand": brand,
            "price": float(getattr(product, "price", 0) or 0),
            "text": " ".join(part for part in text_parts if part).strip(),
        }
    return features


def load_interactions_from_activity(limit_users: int | None = None) -> list[dict[str, Any]]:
    """Derive interactions from the in-house ``UserActivityLog`` table.

    Each activity row contributes an implicit signal weighted by its type. Only
    first-party data from this application is used.

    Args:
        limit_users: Optionally cap the number of distinct users loaded.

    Returns:
        Interaction rows sorted by timestamp.
    """
    from apps.ai_engine.models import UserActivityLog

    weights = {
        "view": 1.0,
        "search": 1.0,
        "cart_add": 3.0,
        "purchase": 5.0,
        "rate": 4.0,
    }
    queryset = (
        UserActivityLog.objects.filter(product__isnull=False, user__isnull=False)
        .select_related("user", "product")
        .order_by("created_at")
    )
    rows: list[dict[str, Any]] = []
    for index, activity in enumerate(queryset.iterator()):
        rows.append(
            {
                "user_id": f"u{activity.user_id}",
                "item_id": str(activity.product_id),
                "weight": weights.get(getattr(activity, "activity_type", "view"), 1.0),
                "timestamp": index,
            }
        )
    if limit_users is not None:
        allowed = sorted({row["user_id"] for row in rows})[:limit_users]
        allowed_set = set(allowed)
        rows = [row for row in rows if row["user_id"] in allowed_set]
    return rows

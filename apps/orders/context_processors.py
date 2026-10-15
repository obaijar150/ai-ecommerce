"""Template context processors for the orders app."""

from .services import CartService


def cart_summary(request):
    """Expose the number of items in the visitor's cart to every template.

    Args:
        request: The current HTTP request.

    Returns:
        A dict with ``cart_item_count`` (int). Returns 0 on any error so the
        storefront never fails to render because of the cart.
    """
    try:
        count = CartService.get_item_count(request)
    except Exception:  # pragma: no cover - defensive: never break page rendering
        count = 0
    return {"cart_item_count": count}

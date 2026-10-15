"""Signal handlers for the orders app."""

from __future__ import annotations

import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .services import CartService

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs) -> None:
    """Move a guest's session cart onto their account after login.

    The guest session key is read from the session data (stored when items were
    added) because Django cycles the session key during login.
    """
    if request is None:
        return
    session_key = request.session.get("guest_cart_key")
    if not session_key:
        return
    try:
        CartService.merge_session_cart(user, session_key)
    except Exception:  # pragma: no cover - never block login on cart errors
        logger.exception("Failed to merge guest cart on login")
    finally:
        request.session.pop("guest_cart_key", None)

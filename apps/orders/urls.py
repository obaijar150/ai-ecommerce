"""
Orders URL patterns.
"""

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path(
        "orders/<uuid:pk>/",
        views.OrderDetailView.as_view(),
        name="order_detail",
    ),
]

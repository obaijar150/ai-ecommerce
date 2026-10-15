"""
Orders URL patterns.
"""

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<slug:slug>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path(
        "orders/<uuid:pk>/",
        views.OrderDetailView.as_view(),
        name="order_detail",
    ),
    path(
        "orders/<uuid:pk>/confirmation/",
        views.OrderConfirmationView.as_view(),
        name="order_confirmation",
    ),
    path("orders/<uuid:pk>/pay/", views.order_pay, name="order_pay"),
    path("orders/<uuid:pk>/cancel/", views.order_cancel, name="order_cancel"),
]

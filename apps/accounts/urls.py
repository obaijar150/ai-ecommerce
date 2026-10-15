"""
Accounts URL patterns.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),

    # Password Reset
    path("password-reset/", views.CustomPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.CustomPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.CustomPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),

    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),

    # Addresses
    path("addresses/", views.AddressListView.as_view(), name="address_list"),
    path("addresses/add/", views.AddressCreateView.as_view(), name="address_add"),
    path(
        "addresses/<int:pk>/edit/",
        views.AddressUpdateView.as_view(),
        name="address_edit",
    ),
    path(
        "addresses/<int:pk>/delete/",
        views.AddressDeleteView.as_view(),
        name="address_delete",
    ),

    # Wishlist
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),

    # Admin redirect
    path("admin-dashboard/", views.admin_dashboard_redirect, name="admin_dashboard"),
]

"""
Catalog URL patterns.
"""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path(
        "products/category/<slug:slug>/",
        views.CategoryDetailView.as_view(),
        name="category_detail",
    ),
    path(
        "products/<slug:slug>/",
        views.ProductDetailView.as_view(),
        name="product_detail",
    ),
]

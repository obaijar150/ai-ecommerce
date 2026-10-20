"""
Analytics URL patterns.
"""

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("sales-report/", views.sales_report, name="sales_report"),
    path("products/", views.ProductManagementListView.as_view(), name="product_list"),
    path("products/add/", views.ProductCreateView.as_view(), name="product_add"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_edit"),
    path(
        "products/<int:pk>/delete/",
        views.ProductDeleteView.as_view(),
        name="product_delete",
    ),
    path("categories/", views.CategoryManagementListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path("stock/", views.StockUpdateView.as_view(), name="stock_update"),
    path("orders/", views.OrderManagementListView.as_view(), name="order_list"),
    path("reviews/", views.ReviewManagementListView.as_view(), name="review_list"),
]

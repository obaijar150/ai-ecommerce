"""
Analytics URL patterns.
"""

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("sales-report/", views.sales_report, name="sales_report"),
]

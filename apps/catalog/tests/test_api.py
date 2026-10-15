"""
Tests for the catalog DRF API: list, detail, filtering, search, read-only
enforcement for anonymous users.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .factories import BrandFactory, CategoryFactory, ProductFactory, TagFactory


class TestProductAPI(TestCase):
    """Test the product API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.category = CategoryFactory(name="Electronics")
        self.brand = BrandFactory(name="Apple")
        self.product = ProductFactory(
            name="iPhone",
            category=self.category,
            brand=self.brand,
            price=Decimal("999.99"),
            stock_quantity=5,
            with_image=True,
        )

    def test_product_list(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_product_detail(self):
        response = self.client.get(f"/api/products/{self.product.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "iPhone")
        self.assertIn("specifications", response.data)

    def test_product_search(self):
        ProductFactory(name="Android Phone")
        response = self.client.get("/api/products/", {"search": "iPhone"})
        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("iPhone", names)
        self.assertNotIn("Android Phone", names)

    def test_product_filter_by_category(self):
        other = CategoryFactory(name="Books")
        ProductFactory(name="Novel", category=other)
        response = self.client.get("/api/products/", {"category": other.pk})
        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Novel", names)
        self.assertNotIn("iPhone", names)

    def test_product_ordering(self):
        ProductFactory(name="Cheap", price=Decimal("1.00"))
        response = self.client.get("/api/products/", {"ordering": "price"})
        self.assertEqual(response.status_code, 200)

    def test_inactive_products_excluded(self):
        ProductFactory(name="Hidden", is_active=False)
        response = self.client.get("/api/products/")
        names = [item["name"] for item in response.data["results"]]
        self.assertNotIn("Hidden", names)

    def test_anonymous_cannot_create_product(self):
        response = self.client.post(
            "/api/products/",
            {"name": "Hacker", "price": "1.00", "sku": "HACK-1", "description": "x"},
        )
        self.assertIn(response.status_code, (401, 403))


class TestCategoryAndBrandAPI(TestCase):
    """Test category, brand and tag API endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_category_list(self):
        CategoryFactory()
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, 200)

    def test_category_children_nested(self):
        parent = CategoryFactory()
        CategoryFactory(parent=parent)
        response = self.client.get(f"/api/categories/{parent.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["children"]), 1)

    def test_tag_list(self):
        TagFactory()
        response = self.client.get("/api/tags/")
        self.assertEqual(response.status_code, 200)

    def test_brand_list(self):
        BrandFactory()
        response = self.client.get("/api/brands/")
        self.assertEqual(response.status_code, 200)

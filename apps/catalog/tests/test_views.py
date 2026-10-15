"""
Tests for catalog views: homepage, product list (filter/sort/paginate/search),
product detail, and category pages.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from .factories import BrandFactory, CategoryFactory, ProductFactory, TagFactory


class TestHomePageView(TestCase):
    """Test the homepage view."""

    def setUp(self):
        self.client = Client()

    def test_homepage_loads(self):
        """Homepage returns 200 and uses the expected template."""
        response = self.client.get(reverse("catalog:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/home.html")

    def test_homepage_shows_featured_products(self):
        """Featured products appear on the homepage."""
        ProductFactory(is_featured=True, name="Featured Item")
        response = self.client.get(reverse("catalog:home"))
        self.assertContains(response, "Featured Item")

    def test_homepage_excludes_inactive_products(self):
        """Inactive featured products do not appear."""
        ProductFactory(is_featured=True, is_active=False, name="Hidden Item")
        response = self.client.get(reverse("catalog:home"))
        self.assertNotContains(response, "Hidden Item")

    def test_homepage_lists_root_categories_only(self):
        """Only top-level categories are shown on the homepage."""
        parent = CategoryFactory(name="TopLevel")
        CategoryFactory(name="SubCategory", parent=parent)
        response = self.client.get(reverse("catalog:home"))
        self.assertContains(response, "TopLevel")
        self.assertNotContains(response, "SubCategory")


class TestProductListView(TestCase):
    """Test product listing with filtering, sorting and pagination."""

    def setUp(self):
        self.client = Client()
        self.category = CategoryFactory(name="Electronics")
        self.brand = BrandFactory(name="Apple")
        self.tag = TagFactory(name="wireless")

        self.iphone = ProductFactory(
            name="iPhone",
            category=self.category,
            brand=self.brand,
            price=Decimal("999.99"),
            stock_quantity=50,
        )
        self.iphone.tags.add(self.tag)
        self.case = ProductFactory(
            name="Cheap Case",
            category=self.category,
            brand=self.brand,
            price=Decimal("19.99"),
            stock_quantity=100,
        )
        ProductFactory(
            name="Out of Stock Item",
            category=self.category,
            price=Decimal("50.00"),
            stock_quantity=0,
        )
        ProductFactory(
            name="Hidden Product",
            category=self.category,
            price=Decimal("100.00"),
            stock_quantity=10,
            is_active=False,
        )

    def test_product_list_loads(self):
        """Product list returns 200."""
        response = self.client.get(reverse("catalog:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/product_list.html")

    def test_product_list_shows_active_products(self):
        """Active products appear in the listing."""
        response = self.client.get(reverse("catalog:product_list"))
        self.assertContains(response, "iPhone")
        self.assertContains(response, "Cheap Case")

    def test_product_list_excludes_inactive(self):
        """Inactive products do not appear."""
        response = self.client.get(reverse("catalog:product_list"))
        self.assertNotContains(response, "Hidden Product")

    def test_filter_by_category(self):
        """Filtering by category excludes other categories' products."""
        other = CategoryFactory(name="Books")
        ProductFactory(name="Novel", category=other, price=Decimal("12.00"))
        response = self.client.get(
            reverse("catalog:product_list"), {"category": self.category.slug}
        )
        self.assertContains(response, "iPhone")
        self.assertNotContains(response, "Novel")

    def test_filter_by_category_includes_subcategory_products(self):
        """Parent category filter includes subcategory products."""
        child = CategoryFactory(name="Phones", parent=self.category)
        ProductFactory(name="Sub Phone", category=child, price=Decimal("500.00"))
        response = self.client.get(
            reverse("catalog:product_list"), {"category": self.category.slug}
        )
        self.assertContains(response, "Sub Phone")

    def test_filter_by_brand(self):
        """Filtering by brand works."""
        response = self.client.get(
            reverse("catalog:product_list"), {"brand": self.brand.slug}
        )
        self.assertContains(response, "iPhone")

    def test_filter_by_tag(self):
        """Filtering by tag works."""
        response = self.client.get(
            reverse("catalog:product_list"), {"tag": self.tag.slug}
        )
        self.assertContains(response, "iPhone")
        self.assertNotContains(response, "Cheap Case")

    def test_filter_in_stock(self):
        """In-stock filter excludes out-of-stock items."""
        response = self.client.get(reverse("catalog:product_list"), {"in_stock": "1"})
        self.assertContains(response, "iPhone")
        self.assertNotContains(response, "Out of Stock Item")

    def test_sort_by_price_ascending(self):
        """Sorting by price low to high."""
        response = self.client.get(reverse("catalog:product_list"), {"sort": "price"})
        prices = [p.current_price for p in response.context["products"]]
        self.assertEqual(prices, sorted(prices))

    def test_sort_by_price_descending(self):
        """Sorting by price high to low."""
        response = self.client.get(reverse("catalog:product_list"), {"sort": "-price"})
        prices = [p.current_price for p in response.context["products"]]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_sort_uses_sale_price(self):
        """Effective price sorting accounts for sale prices."""
        ProductFactory(
            name="OnSale",
            price=Decimal("200.00"),
            sale_price=Decimal("5.00"),
        )
        response = self.client.get(reverse("catalog:product_list"), {"sort": "price"})
        products = list(response.context["products"])
        self.assertEqual(products[0].name, "OnSale")

    def test_filter_by_price_range(self):
        """Price range filter works."""
        response = self.client.get(
            reverse("catalog:product_list"), {"min_price": "100", "max_price": "1000"}
        )
        self.assertContains(response, "iPhone")
        self.assertNotContains(response, "Cheap Case")

    def test_invalid_price_filter_is_ignored(self):
        """A non-numeric price filter does not crash the view."""
        response = self.client.get(
            reverse("catalog:product_list"), {"min_price": "not-a-number"}
        )
        self.assertEqual(response.status_code, 200)

    def test_keyword_search(self):
        """The q parameter performs keyword search."""
        response = self.client.get(reverse("catalog:product_list"), {"q": "iphone"})
        self.assertContains(response, "iPhone")
        self.assertNotContains(response, "Cheap Case")

    def test_pagination(self):
        """Results are paginated at the configured page size."""
        for i in range(15):
            ProductFactory(name=f"Extra {i}", price=Decimal("10.00"))
        response = self.client.get(reverse("catalog:product_list"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["products"]), 12)

    def test_pagination_preserves_query_params(self):
        """Pagination links keep the active filters."""
        for i in range(15):
            ProductFactory(name=f"Extra {i}", price=Decimal("10.00"))
        response = self.client.get(
            reverse("catalog:product_list"), {"sort": "price"}
        )
        self.assertIn("sort=price", response.context["query_params"])


class TestProductDetailView(TestCase):
    """Test the product detail page."""

    def setUp(self):
        self.client = Client()
        self.product = ProductFactory(
            name="Test Product",
            slug="test-product",
            price=Decimal("49.99"),
            stock_quantity=25,
            description="A great product for testing.",
            specifications={"color": "blue", "weight": "1kg"},
        )

    def test_detail_page_loads(self):
        """Product detail returns 200."""
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": "test-product"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/product_detail.html")

    def test_detail_shows_product_info(self):
        """Detail page shows name, price and description."""
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": "test-product"})
        )
        self.assertContains(response, "Test Product")
        self.assertContains(response, "49.99")
        self.assertContains(response, "A great product for testing.")

    def test_detail_shows_specifications(self):
        """Specifications are rendered on the page."""
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": "test-product"})
        )
        self.assertContains(response, "blue")
        self.assertContains(response, "weight")

    def test_detail_increments_view_count(self):
        """Viewing a product increments its view count."""
        self.client.get(reverse("catalog:product_detail", kwargs={"slug": "test-product"}))
        self.product.refresh_from_db()
        self.assertEqual(self.product.view_count, 1)

    def test_detail_404_for_invalid_slug(self):
        """A non-existent product returns 404."""
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": "does-not-exist"})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_404_for_inactive_product(self):
        """Inactive products are not visible."""
        ProductFactory(slug="inactive", is_active=False)
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": "inactive"})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_out_of_stock(self):
        """Out of stock message appears for zero-quantity products."""
        product = ProductFactory(stock_quantity=0)
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "Out of Stock")

    def test_detail_shows_related_products(self):
        """Related products from the same category appear."""
        category = CategoryFactory()
        product = ProductFactory(category=category, name="Main Product")
        ProductFactory(category=category, name="Related Product")
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "Related Product")


class TestCategoryDetailView(TestCase):
    """Test the category detail page."""

    def setUp(self):
        self.client = Client()
        self.category = CategoryFactory(name="Electronics", slug="electronics")
        self.child = CategoryFactory(name="Phones", parent=self.category)

    def test_category_page_loads(self):
        """Category page returns 200."""
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/category_detail.html")

    def test_category_page_lists_products(self):
        """Products in the category and its children are listed."""
        ProductFactory(name="Parent Product", category=self.category)
        ProductFactory(name="Child Product", category=self.child)
        response = self.client.get(self.category.get_absolute_url())
        self.assertContains(response, "Parent Product")
        self.assertContains(response, "Child Product")

    def test_category_page_404(self):
        """Unknown category slug returns 404."""
        response = self.client.get("/products/category/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_category_page_shows_subcategories(self):
        """Subcategory navigation is present."""
        response = self.client.get(self.category.get_absolute_url())
        self.assertContains(response, "Phones")

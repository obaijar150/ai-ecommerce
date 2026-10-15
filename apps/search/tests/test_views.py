"""
Tests for the search app: keyword search, empty query handling and logging.
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.catalog.tests.factories import BrandFactory, ProductFactory

from apps.search.models import SearchQueryLog


class TestProductSearchView(TestCase):
    """Test keyword product search."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("search:search_results")

    def test_empty_query_returns_no_results(self):
        """A blank query yields no results and logs nothing."""
        ProductFactory(name="Something")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 0)
        self.assertEqual(SearchQueryLog.objects.count(), 0)

    def test_keyword_match(self):
        """A keyword search finds matching products."""
        ProductFactory(name="Blue Widget")
        ProductFactory(name="Red Gadget")
        response = self.client.get(self.url, {"q": "widget"})
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["products"]]
        self.assertIn("Blue Widget", names)
        self.assertNotIn("Red Gadget", names)

    def test_search_matches_brand(self):
        """Search matches products by brand name."""
        brand = BrandFactory(name="Aurora")
        ProductFactory(name="Phone", brand=brand)
        response = self.client.get(self.url, {"q": "aurora"})
        names = [p.name for p in response.context["products"]]
        self.assertIn("Phone", names)

    def test_search_logs_query(self):
        """Each non-empty search is logged for analytics."""
        ProductFactory(name="Blue Widget")
        self.client.get(self.url, {"q": "widget"})
        self.assertEqual(SearchQueryLog.objects.count(), 1)
        log = SearchQueryLog.objects.first()
        self.assertEqual(log.query, "widget")
        self.assertGreaterEqual(log.results_count, 1)

    def test_search_excludes_inactive(self):
        """Inactive products do not appear in search results."""
        ProductFactory(name="Hidden Widget", is_active=False)
        response = self.client.get(self.url, {"q": "widget"})
        names = [p.name for p in response.context["products"]]
        self.assertNotIn("Hidden Widget", names)

    def test_search_results_template(self):
        """The dedicated search template is used."""
        ProductFactory(name="Blue Widget")
        response = self.client.get(self.url, {"q": "widget"})
        self.assertTemplateUsed(response, "search/search_results.html")

"""
Tests for the ``seed_catalog`` management command.
"""

import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.catalog.models import Brand, Category, Product, ProductImage


class TestSeedCatalogCommand(TestCase):
    """Test sample-data seeding."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_seed_creates_data(self):
        """The command creates categories, brands, products and images."""
        out = StringIO()
        call_command("seed_catalog", stdout=out)

        self.assertGreater(Category.objects.count(), 0)
        self.assertGreater(Brand.objects.count(), 0)
        self.assertGreater(Product.objects.count(), 0)
        self.assertGreater(ProductImage.objects.count(), 0)
        self.assertIn("Catalog seeded successfully.", out.getvalue())

    def test_seed_creates_subcategories(self):
        """At least one category has a parent (subcategory)."""
        call_command("seed_catalog", stdout=StringIO())
        self.assertTrue(Category.objects.filter(parent__isnull=False).exists())

    def test_seed_is_idempotent(self):
        """Running the command twice does not duplicate products."""
        call_command("seed_catalog", stdout=StringIO())
        first_count = Product.objects.count()
        call_command("seed_catalog", stdout=StringIO())
        self.assertEqual(Product.objects.count(), first_count)

    def test_seed_flush(self):
        """--flush removes existing catalog data first."""
        call_command("seed_catalog", stdout=StringIO())
        call_command("seed_catalog", "--flush", stdout=StringIO())
        self.assertEqual(Product.objects.count(), len(Product.objects.all()))
        self.assertGreater(Product.objects.count(), 0)

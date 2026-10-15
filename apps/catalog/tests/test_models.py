"""
Tests for catalog models: Category, Brand, Tag, Product, ProductImage,
ProductInventory, plus queryset helpers and inventory validation.
"""

from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product

from .factories import (
    BrandFactory,
    CategoryFactory,
    ProductFactory,
    ProductImageFactory,
    ProductInventoryFactory,
    TagFactory,
)


class TestCategoryModel(TestCase):
    """Test Category model behaviour."""

    def test_category_creation_generates_slug(self):
        """A slug is generated from the name when omitted."""
        category = CategoryFactory(name="Electronics")
        self.assertEqual(category.name, "Electronics")
        self.assertEqual(category.slug, "electronics")
        self.assertTrue(category.is_active)

    def test_subcategory_relationship(self):
        """Categories can have parent-child relationships."""
        parent = CategoryFactory(name="Electronics")
        child = CategoryFactory(name="Phones", parent=parent)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())
        self.assertTrue(parent.is_root)
        self.assertFalse(child.is_root)

    def test_get_descendants(self):
        """get_descendants returns nested children."""
        parent = CategoryFactory()
        child = CategoryFactory(parent=parent)
        grandchild = CategoryFactory(parent=child)
        descendants = parent.get_descendants(include_self=True)
        self.assertIn(parent, descendants)
        self.assertIn(child, descendants)
        self.assertIn(grandchild, descendants)

    def test_product_count_only_counts_active(self):
        """product_count ignores inactive products."""
        category = CategoryFactory()
        ProductFactory(category=category, is_active=True)
        ProductFactory(category=category, is_active=False)
        self.assertEqual(category.product_count, 1)

    def test_category_get_absolute_url(self):
        """Category has a valid URL."""
        category = CategoryFactory(slug="electronics")
        self.assertEqual(category.get_absolute_url(), "/products/category/electronics/")


class TestBrandModel(TestCase):
    """Test Brand model behaviour."""

    def test_brand_creation_generates_slug(self):
        """A slug is generated from the name when omitted."""
        brand = BrandFactory(name="Apple")
        self.assertEqual(brand.name, "Apple")
        self.assertEqual(brand.slug, "apple")
        self.assertTrue(brand.is_active)

    def test_brand_product_count(self):
        """Brand exposes related products."""
        brand = BrandFactory()
        ProductFactory(brand=brand)
        ProductFactory(brand=brand)
        self.assertEqual(brand.products.count(), 2)


class TestTagModel(TestCase):
    """Test Tag model behaviour."""

    def test_tag_slug_generated(self):
        """Tag slug is generated automatically."""
        tag = TagFactory(name="Wireless")
        self.assertEqual(tag.slug, "wireless")


class TestProductModel(TestCase):
    """Test Product model behaviour and computed properties."""

    def test_product_creation(self):
        """Product stores all core fields."""
        product = ProductFactory(
            name="Test Product",
            price=Decimal("29.99"),
            sku="TEST-001",
            stock_quantity=50,
        )
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, Decimal("29.99"))
        self.assertEqual(product.sku, "TEST-001")
        self.assertEqual(product.stock_quantity, 50)
        self.assertTrue(product.is_active)

    def test_product_slug_auto_generated(self):
        """Slug is auto-generated from the name if not provided."""
        product = ProductFactory(name="Amazing Gadget Pro", slug="")
        self.assertEqual(product.slug, "amazing-gadget-pro")

    def test_current_price_no_sale(self):
        """Current price equals regular price when no sale."""
        product = ProductFactory(price=Decimal("50.00"), sale_price=None)
        self.assertEqual(product.current_price, Decimal("50.00"))

    def test_current_price_with_sale(self):
        """Current price equals sale price when on sale."""
        product = ProductFactory(price=Decimal("100.00"), sale_price=Decimal("75.00"))
        self.assertEqual(product.current_price, Decimal("75.00"))

    def test_discount_percentage(self):
        """Discount percentage is calculated correctly."""
        product = ProductFactory(price=Decimal("100.00"), sale_price=Decimal("75.00"))
        self.assertEqual(product.discount_percentage, 25.0)

    def test_no_discount(self):
        """No discount when sale price is not set."""
        product = ProductFactory(price=Decimal("50.00"), sale_price=None)
        self.assertEqual(product.discount_percentage, 0)

    def test_in_stock_and_low_stock(self):
        """Stock helpers reflect quantity thresholds."""
        product = ProductFactory(stock_quantity=10, low_stock_threshold=10)
        self.assertTrue(product.in_stock)
        self.assertTrue(product.is_low_stock)
        full = ProductFactory(stock_quantity=100, low_stock_threshold=10)
        self.assertFalse(full.is_low_stock)

    def test_out_of_stock(self):
        """Product is out of stock when quantity is 0."""
        product = ProductFactory(stock_quantity=0)
        self.assertFalse(product.in_stock)
        self.assertFalse(product.is_low_stock)

    def test_get_absolute_url(self):
        """Product has a valid URL."""
        product = ProductFactory(slug="test-widget")
        self.assertEqual(product.get_absolute_url(), "/products/test-widget/")

    def test_specifications_json_roundtrip(self):
        """Specifications are stored and retrieved as a dict."""
        specs = {"color": "red", "size": "L"}
        product = ProductFactory(specifications=specs)
        product.refresh_from_db()
        self.assertEqual(product.specifications, specs)

    def test_refresh_rating(self):
        """refresh_rating recomputes average and count from reviews."""
        from apps.reviews.models import Review
        from apps.accounts.tests.factories import UserFactory

        product = ProductFactory()
        user = UserFactory()
        Review.objects.create(product=product, user=user, rating=4, title="Good", body="Nice")
        product.refresh_rating()
        product.refresh_from_db()
        self.assertEqual(product.review_count, 1)
        self.assertEqual(product.average_rating, Decimal("4.00"))


class TestProductQuerySet(TestCase):
    """Test custom ProductQuerySet helpers."""

    def test_search_matches_name_and_description(self):
        """Search matches across name and description case-insensitively."""
        ProductFactory(name="Blue Widget", description="A widget")
        ProductFactory(name="Red Gadget", description="nothing to see")
        self.assertEqual(Product.objects.search("widget").count(), 1)
        self.assertEqual(Product.objects.search("WIDGET").count(), 1)

    def test_search_multiple_terms_are_anded(self):
        """All search terms must match."""
        ProductFactory(name="Blue Widget", description="portable and blue")
        ProductFactory(name="Blue Gadget", description="portable and blue")
        # "widget" only matches one of the two; combined with "blue" still one.
        self.assertEqual(Product.objects.search("blue widget").count(), 1)

    def test_search_matches_brand_and_sku(self):
        """Search matches brand name and SKU."""
        brand = BrandFactory(name="Aurora")
        ProductFactory(brand=brand, name="Phone", sku="AUR-100")
        self.assertEqual(Product.objects.search("aurora").count(), 1)
        self.assertEqual(Product.objects.search("AUR-100").count(), 1)

    def test_search_blank_returns_all(self):
        """Blank query returns the full queryset."""
        ProductFactory()
        self.assertEqual(Product.objects.search("   ").count(), 1)

    def test_with_effective_price(self):
        """effective_price uses the sale price when present."""
        ProductFactory(price=Decimal("50.00"), sale_price=Decimal("30.00"))
        product = Product.objects.with_effective_price().get()
        self.assertEqual(product.effective_price, Decimal("30.00"))


class TestProductImageModel(TestCase):
    """Test ProductImage model and primary-image selection."""

    def test_image_creation_with_real_bytes(self):
        """An image with valid bytes can be created."""
        image = ProductImageFactory()
        self.assertTrue(image.image.name)
        self.assertTrue(image.is_primary)

    def test_primary_image_property(self):
        """Product.primary_image returns primary, otherwise the first image."""
        product = ProductFactory()
        self.assertIsNone(product.primary_image)
        secondary = ProductImageFactory(product=product, is_primary=False, sort_order=1)
        self.assertEqual(product.primary_image, secondary)
        primary = ProductImageFactory(product=product, is_primary=True)
        self.assertEqual(product.primary_image, primary)


class TestInventoryModel(TestCase):
    """Test ProductInventory behaviour and validation."""

    def test_inventory_creation(self):
        """Inventory tracks quantity and reservations."""
        inventory = ProductInventoryFactory(quantity=100, reserved_quantity=10)
        self.assertEqual(inventory.quantity, 100)
        self.assertEqual(inventory.reserved_quantity, 10)
        self.assertEqual(inventory.available_quantity, 90)

    def test_available_quantity_never_negative(self):
        """available_quantity is clamped at zero."""
        inventory = ProductInventoryFactory(quantity=5, reserved_quantity=10)
        self.assertEqual(inventory.available_quantity, 0)

    def test_needs_reorder(self):
        """Reorder is triggered when stock is at/below reorder level."""
        inventory = ProductInventoryFactory(quantity=5, reorder_level=10)
        self.assertTrue(inventory.needs_reorder)

    def test_no_reorder_needed(self):
        """No reorder when stock is sufficient."""
        inventory = ProductInventoryFactory(quantity=50, reorder_level=10)
        self.assertFalse(inventory.needs_reorder)

    def test_inventory_product_relationship(self):
        """Inventory is linked to a single product."""
        inventory = ProductInventoryFactory()
        self.assertEqual(inventory.product.inventory, inventory)

    def test_reserve_valid_amount(self):
        """Reserving stock updates reserved_quantity."""
        inventory = ProductInventoryFactory(quantity=10, reserved_quantity=0)
        inventory.reserve(4)
        inventory.refresh_from_db()
        self.assertEqual(inventory.reserved_quantity, 4)
        self.assertEqual(inventory.available_quantity, 6)

    def test_reserve_more_than_available_raises(self):
        """Reserving beyond availability raises ValueError."""
        inventory = ProductInventoryFactory(quantity=3, reserved_quantity=0)
        with self.assertRaises(ValueError):
            inventory.reserve(5)

    def test_reserve_non_positive_raises(self):
        """Reserving a non-positive amount raises ValueError."""
        inventory = ProductInventoryFactory(quantity=10)
        with self.assertRaises(ValueError):
            inventory.reserve(0)

    def test_release_never_goes_negative(self):
        """Releasing more than reserved clamps to zero."""
        inventory = ProductInventoryFactory(quantity=10, reserved_quantity=2)
        inventory.release(5)
        inventory.refresh_from_db()
        self.assertEqual(inventory.reserved_quantity, 0)

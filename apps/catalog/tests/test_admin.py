"""
Tests for Django admin CRUD of products, categories, brands, tags and
inventory. These exercise the real admin views, including inline formsets.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from .factories import BrandFactory, CategoryFactory, ProductFactory, TagFactory

User = get_user_model()


def inline_management(prefix: str, total: int = 0, initial: int = 0) -> dict:
    """Build the management-form fields Django expects for an inline formset."""
    return {
        f"{prefix}-TOTAL_FORMS": total,
        f"{prefix}-INITIAL_FORMS": initial,
        f"{prefix}-MIN_NUM_FORMS": 0,
        f"{prefix}-MAX_NUM_FORMS": 1000,
    }


def product_admin_data(**overrides) -> dict:
    """Return a complete, valid payload for the Product admin add/change form."""
    data = {
        "name": "Admin Product",
        "slug": "admin-product",
        "sku": "ADM-001",
        "description": "Created via admin",
        "price": "29.99",
        "sale_price": "",
        "stock_quantity": 50,
        "low_stock_threshold": 10,
        "weight_kg": "",
        "specifications": "{}",
        "is_active": "on",
        "tags": [],
    }
    data.update(overrides)
    data.update(inline_management("images", total=0))
    data.update(inline_management("inventory", total=0))
    return data


class AdminTestCase(TestCase):
    """Base class with a logged-in superuser client."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass12345"
        )
        self.client = Client()
        self.client.force_login(self.admin)


class TestAdminPagesLoad(AdminTestCase):
    """Smoke-test the main catalog admin pages."""

    def test_admin_index_loads(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_product_changelist_loads(self):
        ProductFactory()
        response = self.client.get("/admin/catalog/product/")
        self.assertEqual(response.status_code, 200)

    def test_product_changelist_with_sale_price(self):
        """A product on sale must not break the changelist (format_html)."""
        ProductFactory(price=Decimal("100.00"), sale_price=Decimal("75.00"))
        response = self.client.get("/admin/catalog/product/")
        self.assertEqual(response.status_code, 200)

    def test_product_changelist_with_reviews(self):
        """A rated product must not break the changelist (format_html)."""
        product = ProductFactory()
        product.average_rating = Decimal("4.50")
        product.review_count = 2
        product.save(update_fields=["average_rating", "review_count"])
        response = self.client.get("/admin/catalog/product/")
        self.assertEqual(response.status_code, 200)

    def test_category_changelist_loads(self):
        CategoryFactory()
        response = self.client.get("/admin/catalog/category/")
        self.assertEqual(response.status_code, 200)

    def test_brand_changelist_loads(self):
        BrandFactory()
        response = self.client.get("/admin/catalog/brand/")
        self.assertEqual(response.status_code, 200)

    def test_inventory_changelist_loads(self):
        ProductFactory(with_inventory=True)
        response = self.client.get("/admin/catalog/productinventory/")
        self.assertEqual(response.status_code, 200)

    def test_user_changelist_loads(self):
        response = self.client.get("/admin/auth/user/")
        self.assertEqual(response.status_code, 200)


class TestProductAdminCRUD(AdminTestCase):
    """Test creating, editing and deleting products via the admin."""

    def test_create_product(self):
        category = CategoryFactory()
        brand = BrandFactory()
        payload = product_admin_data(
            category=category.pk, brand=brand.pk, sku="NEW-100"
        )
        response = self.client.post("/admin/catalog/product/add/", payload)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        from apps.catalog.models import Product

        self.assertTrue(Product.objects.filter(sku="NEW-100").exists())

    def test_create_product_with_inline_image_and_inventory(self):
        from apps.catalog.models import Product, ProductImage, ProductInventory
        from .factories import make_test_image

        upload = SimpleUploadedFile(
            "inline.png", make_test_image().read(), content_type="image/png"
        )
        payload = product_admin_data(sku="INLINE-1")
        payload.update(
            inline_management("images", total=1),
        )
        payload.update(
            {
                "images-0-image": upload,
                "images-0-alt_text": "inline image",
                "images-0-sort_order": 0,
            }
        )
        payload.update(inline_management("inventory", total=1))
        payload.update(
            {
                "inventory-0-quantity": 25,
                "inventory-0-reserved_quantity": 0,
                "inventory-0-reorder_level": 5,
                "inventory-0-last_restocked": "",
            }
        )
        response = self.client.post("/admin/catalog/product/add/", payload)
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(sku="INLINE-1")
        self.assertEqual(product.images.count(), 1)
        self.assertTrue(ProductInventory.objects.filter(product=product).exists())

    def test_edit_product(self):
        product = ProductFactory(name="Old Name", price=Decimal("10.00"))
        payload = product_admin_data(
            name="Updated Name",
            slug=product.slug,
            sku=product.sku,
            price="15.00",
            stock_quantity=product.stock_quantity,
        )
        response = self.client.post(
            f"/admin/catalog/product/{product.pk}/change/", payload
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.name, "Updated Name")
        self.assertEqual(product.price, Decimal("15.00"))

    def test_delete_product(self):
        from apps.catalog.models import Product

        product = ProductFactory()
        response = self.client.post(
            f"/admin/catalog/product/{product.pk}/delete/", {"post": "yes"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_product_search_in_admin(self):
        ProductFactory(name="Findable Widget")
        ProductFactory(name="Other Thing")
        response = self.client.get("/admin/catalog/product/", {"q": "Findable"})
        self.assertContains(response, "Findable Widget")
        self.assertNotContains(response, "Other Thing")

    def test_low_stock_filter(self):
        ProductFactory(name="Empty One", stock_quantity=0)
        ProductFactory(name="Full One", stock_quantity=100)
        response = self.client.get(
            "/admin/catalog/product/", {"stock_level": "out"}
        )
        self.assertContains(response, "Empty One")
        self.assertNotContains(response, "Full One")


class TestCategoryAdminCRUD(AdminTestCase):
    """Test category (and subcategory) admin management."""

    def test_create_category(self):
        response = self.client.post(
            "/admin/catalog/category/add/",
            {"name": "New Category", "slug": "new-category", "sort_order": 0},
        )
        self.assertEqual(response.status_code, 302)
        from apps.catalog.models import Category

        self.assertTrue(Category.objects.filter(slug="new-category").exists())

    def test_create_subcategory(self):
        parent = CategoryFactory()
        response = self.client.post(
            "/admin/catalog/category/add/",
            {
                "name": "Child Category",
                "slug": "child-category",
                "parent": parent.pk,
                "sort_order": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        parent.refresh_from_db()
        self.assertEqual(parent.children.count(), 1)


class TestBrandAndTagAdminCRUD(AdminTestCase):
    """Test brand and tag admin management."""

    def test_create_brand(self):
        response = self.client.post(
            "/admin/catalog/brand/add/",
            {"name": "New Brand", "slug": "new-brand"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BrandFactory._meta.model.objects.filter(slug="new-brand").exists())

    def test_create_tag(self):
        response = self.client.post(
            "/admin/catalog/tag/add/",
            {"name": "New Tag", "slug": "new-tag"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TagFactory._meta.model.objects.filter(slug="new-tag").exists())


class TestInventoryAdmin(AdminTestCase):
    """Test inventory admin management."""

    def test_edit_inventory(self):
        product = ProductFactory()
        response = self.client.post(
            "/admin/catalog/productinventory/add/",
            {
                "product": product.pk,
                "quantity": 40,
                "reserved_quantity": 5,
                "reorder_level": 10,
                "last_restocked": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.inventory.quantity, 40)
        self.assertEqual(product.inventory.available_quantity, 35)

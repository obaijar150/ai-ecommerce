"""
Tests for the custom staff-only admin dashboard and management pages.

Covers access control (staff only), product/category management, stock
updates, order status updates, and review moderation.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import (
    CategoryFactory,
    ProductFactory,
    make_test_image,
)
from apps.orders.tests.factories import OrderFactory
from apps.reviews.tests.factories import ReviewFactory

from apps.catalog.models import Product, ProductImage
from apps.orders.models import Order
from apps.reviews.models import Review


class AdminAccessControlTests(TestCase):
    """All admin management pages must be restricted to staff users."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.user = UserFactory(password=None)

    def _staff_urls(self):
        return [
            reverse("analytics:dashboard"),
            reverse("analytics:sales_report"),
            reverse("analytics:product_list"),
            reverse("analytics:product_add"),
            reverse("analytics:category_list"),
            reverse("analytics:category_add"),
            reverse("analytics:stock_update"),
            reverse("analytics:order_list"),
            reverse("analytics:review_list"),
        ]

    def test_anonymous_redirected_to_login(self):
        """Anonymous visitors are sent to the login page."""
        for url in self._staff_urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn("/accounts/login/", response.url)

    def test_non_staff_forbidden(self):
        """Authenticated non-staff users receive 403."""
        self.client.force_login(self.user)
        for url in self._staff_urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, url)

    def test_staff_can_access_all_pages(self):
        """Staff users receive 200 on every management page."""
        self.client.force_login(self.staff)
        for url in self._staff_urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)


class ProductManagementTests(TestCase):
    """Staff product create/edit flows."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.client.force_login(self.staff)

    def test_create_product(self):
        """Posting the form creates a product with the given data."""
        response = self.client.post(
            reverse("analytics:product_add"),
            {
                "name": "Admin Widget",
                "slug": "admin-widget",
                "description": "Made by staff.",
                "price": "19.99",
                "sku": "ADMIN-001",
                "stock_quantity": 5,
                "low_stock_threshold": 10,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(sku="ADMIN-001")
        self.assertEqual(product.name, "Admin Widget")
        self.assertEqual(product.price, Decimal("19.99"))

    def test_edit_product_updates_stock(self):
        """Editing a product persists the new stock quantity."""
        product = ProductFactory(stock_quantity=1)
        response = self.client.post(
            reverse("analytics:product_edit", kwargs={"pk": product.pk}),
            {
                "name": product.name,
                "slug": product.slug,
                "description": product.description,
                "price": str(product.price),
                "sku": product.sku,
                "stock_quantity": 42,
                "low_stock_threshold": product.low_stock_threshold,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 42)

    def test_create_product_with_image(self):
        """Uploading an image stores it as the product's primary image."""
        response = self.client.post(
            reverse("analytics:product_add"),
            {
                "name": "Imaged Widget",
                "description": "Comes with a picture.",
                "price": "9.99",
                "sku": "ADMIN-IMG-1",
                "stock_quantity": 3,
                "low_stock_threshold": 5,
                "is_active": "on",
                "image": make_test_image(),
                "image_alt_text": "A small widget",
            },
        )
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(sku="ADMIN-IMG-1")
        image = product.images.get()
        self.assertTrue(image.is_primary)
        self.assertEqual(image.alt_text, "A small widget")

    def test_edit_product_replaces_primary_image(self):
        """A new upload becomes the sole primary image."""
        product = ProductFactory()
        ProductImage.objects.create(
            product=product, image=make_test_image(), is_primary=True
        )
        response = self.client.post(
            reverse("analytics:product_edit", kwargs={"pk": product.pk}),
            {
                "name": product.name,
                "description": product.description,
                "price": str(product.price),
                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "low_stock_threshold": product.low_stock_threshold,
                "is_active": "on",
                "image": make_test_image(color=(10, 200, 90)),
            },
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.images.filter(is_primary=True).count(), 1)
        self.assertEqual(product.images.count(), 2)

    def test_product_form_has_image_field(self):
        """The product form exposes an image upload control."""
        response = self.client.get(reverse("analytics:product_add"))
        self.assertContains(response, 'type="file"')
        self.assertContains(response, 'name="image"')

    def test_product_list_shows_delete_link(self):
        """Each product row links to its delete confirmation page."""
        product = ProductFactory()
        response = self.client.get(reverse("analytics:product_list"))
        self.assertContains(
            response,
            reverse("analytics:product_delete", kwargs={"pk": product.pk}),
        )


class ProductDeleteTests(TestCase):
    """Staff product deletion flow."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.user = UserFactory(password=None)

    def test_confirmation_page_renders(self):
        """Staff see a confirmation page for the product."""
        self.client.force_login(self.staff)
        product = ProductFactory()
        response = self.client.get(
            reverse("analytics:product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.name)

    def test_get_does_not_delete(self):
        """A GET on the delete URL only shows the confirmation form."""
        self.client.force_login(self.staff)
        product = ProductFactory()
        self.client.get(reverse("analytics:product_delete", kwargs={"pk": product.pk}))
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_delete_product(self):
        """Posting the confirmation form deletes the product."""
        self.client.force_login(self.staff)
        product = ProductFactory()
        response = self.client.post(
            reverse("analytics:product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_delete_removes_image_file(self):
        """Deleting a product also removes its stored image files."""
        self.client.force_login(self.staff)
        product = ProductFactory()
        image = ProductImage.objects.create(
            product=product, image=make_test_image(), is_primary=True
        )
        storage, name = image.image.storage, image.image.name
        self.assertTrue(storage.exists(name))

        self.client.post(
            reverse("analytics:product_delete", kwargs={"pk": product.pk})
        )
        self.assertFalse(storage.exists(name))

    def test_non_staff_cannot_delete(self):
        """Non-staff users get 403 and the product survives."""
        self.client.force_login(self.user)
        product = ProductFactory()
        response = self.client.post(
            reverse("analytics:product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_anonymous_cannot_delete(self):
        """Anonymous users are redirected and the product survives."""
        product = ProductFactory()
        response = self.client.post(
            reverse("analytics:product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())


class CategoryManagementTests(TestCase):
    """Staff category create flow."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.client.force_login(self.staff)

    def test_create_category(self):
        """Posting the form creates a category."""
        response = self.client.post(
            reverse("analytics:category_add"),
            {"name": "Gadgets", "slug": "gadgets", "description": "All gadgets"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.client.get(reverse("analytics:category_list"))
            .context["categories"]
            .filter(name="Gadgets")
            .exists()
        )


class StockUpdateTests(TestCase):
    """Staff stock adjustment flow."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.client.force_login(self.staff)

    def test_update_stock(self):
        """Posting a quantity updates the product stock."""
        product = ProductFactory(stock_quantity=2, low_stock_threshold=10)
        response = self.client.post(
            reverse("analytics:stock_update"),
            {"product_id": product.pk, "quantity": 50},
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 50)

    def test_invalid_quantity_ignored(self):
        """A negative or non-numeric quantity leaves stock unchanged."""
        product = ProductFactory(stock_quantity=7)
        self.client.post(
            reverse("analytics:stock_update"),
            {"product_id": product.pk, "quantity": "abc"},
        )
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 7)


class OrderManagementTests(TestCase):
    """Staff order status updates."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.client.force_login(self.staff)

    def test_update_order_status(self):
        """A valid status change is persisted."""
        order = OrderFactory(status=Order.Status.PENDING)
        response = self.client.post(
            reverse("analytics:order_list"),
            {"order_id": order.pk, "status": Order.Status.SHIPPED},
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_invalid_status_rejected(self):
        """An unknown status value is ignored."""
        order = OrderFactory(status=Order.Status.PENDING)
        self.client.post(
            reverse("analytics:order_list"),
            {"order_id": order.pk, "status": "bogus"},
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_status_filter(self):
        """The queryset is filtered by the status query param."""
        OrderFactory(status=Order.Status.PAID)
        OrderFactory(status=Order.Status.PENDING)
        response = self.client.get(reverse("analytics:order_list"), {"status": "paid"})
        self.assertEqual(response.status_code, 200)
        statuses = {o.status for o in response.context["orders"]}
        self.assertEqual(statuses, {Order.Status.PAID})


class ReviewModerationTests(TestCase):
    """Staff review moderation."""

    def setUp(self):
        self.client = Client()
        self.staff = UserFactory(is_staff=True, password=None)
        self.client.force_login(self.staff)

    def test_delete_review(self):
        """Posting the delete action removes the review."""
        review = ReviewFactory()
        response = self.client.post(
            reverse("analytics:review_list"),
            {"review_id": review.pk, "action": "delete"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

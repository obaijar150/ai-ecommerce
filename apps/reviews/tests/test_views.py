"""
Tests for review creation, listing, ratings aggregation, verified-purchase
detection, and the helpful endpoint.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import ProductFactory

from .factories import ReviewFactory
from apps.reviews.models import Review


class TestReviewCreateView(TestCase):
    """Test creating reviews through the view."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(password=None)
        self.product = ProductFactory()

    def test_login_required(self):
        """Anonymous users are redirected to login."""
        url = reverse("reviews:review_create", kwargs={"product_slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_form_renders_for_logged_in_user(self):
        """A logged-in user sees the review form."""
        self.client.force_login(self.user)
        url = reverse("reviews:review_create", kwargs={"product_slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reviews/review_form.html")

    def test_create_review_updates_rating(self):
        """Posting a valid review saves it and updates aggregates."""
        self.client.force_login(self.user)
        url = reverse("reviews:review_create", kwargs={"product_slug": self.product.slug})
        response = self.client.post(
            url, {"rating": 4, "title": "Good", "body": "Nicely built."}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Review.objects.filter(product=self.product, user=self.user).exists()
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.review_count, 1)
        self.assertEqual(self.product.average_rating, Decimal("4.00"))

    def test_cannot_review_twice(self):
        """A user cannot leave two reviews for the same product."""
        ReviewFactory(product=self.product, user=self.user)
        self.client.force_login(self.user)
        url = reverse("reviews:review_create", kwargs={"product_slug": self.product.slug})
        response = self.client.post(
            url, {"rating": 1, "title": "Bad", "body": "Changed my mind."}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Review.objects.filter(product=self.product, user=self.user).count(), 1
        )

    def test_verified_purchase_flag(self):
        """A review is flagged verified when the user ordered the product."""
        from apps.orders.models import Order, OrderItem

        order = Order.objects.create(
            user=self.user,
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price=Decimal("10.00"),
            total_price=Decimal("10.00"),
        )
        self.client.force_login(self.user)
        url = reverse("reviews:review_create", kwargs={"product_slug": self.product.slug})
        self.client.post(url, {"rating": 5, "title": "Great", "body": "Love it."})
        review = Review.objects.get(product=self.product, user=self.user)
        self.assertTrue(review.is_verified_purchase)


class TestReviewListView(TestCase):
    """Test the review listing page."""

    def setUp(self):
        self.client = Client()
        self.product = ProductFactory()

    def test_review_list_loads(self):
        """Review list returns 200 and shows reviews."""
        ReviewFactory(product=self.product, title="Excellent")
        response = self.client.get(
            reverse("reviews:review_list", kwargs={"product_slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Excellent")

    def test_review_list_empty(self):
        """A product with no reviews renders the empty state."""
        response = self.client.get(
            reverse("reviews:review_list", kwargs={"product_slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 200)


class TestMarkHelpful(TestCase):
    """Test the mark-helpful endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(password=None)
        self.review = ReviewFactory()

    def test_requires_login(self):
        response = self.client.post(
            reverse("reviews:mark_helpful", kwargs={"review_id": self.review.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("reviews:mark_helpful", kwargs={"review_id": self.review.pk})
        )
        self.assertEqual(response.status_code, 405)

    def test_marks_helpful(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("reviews:mark_helpful", kwargs={"review_id": self.review.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["helpful_count"], 1)
        self.review.refresh_from_db()
        self.assertEqual(self.review.helpful_count, 1)

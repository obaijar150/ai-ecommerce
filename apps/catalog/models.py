"""
Catalog models: Brand, Category, Tag, Product, ProductImage, ProductInventory.

Design notes
------------
* Categories are a self-referential tree (subcategories via ``parent``).
* ``Product.current_price`` is the sale price when present, else the regular
  price. Because it is a Python property it cannot be used directly in a
  database filter; use :meth:`ProductQuerySet.with_effective_price` to filter
  and sort on the effective price at the database level.
* Image uploads pass through validators that enforce the allow-listed
  extensions, a maximum size, and a real content-type check.
"""

from decimal import Decimal

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.text import slugify

from .validators import (
    ALLOWED_IMAGE_EXTENSIONS,
    validate_image_content_type,
    validate_image_size,
)


class Brand(models.Model):
    """Product brand/manufacturer."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(
        upload_to="brands/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
            validate_image_content_type,
        ],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "brand"
        verbose_name_plural = "brands"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    """Product category with self-referential hierarchy (supports subcategories)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
            validate_image_content_type,
        ],
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["slug"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_root(self) -> bool:
        """Return True when this category has no parent."""
        return self.parent_id is None

    @property
    def product_count(self) -> int:
        """Count active products in this category (excluding children)."""
        return self.products.filter(is_active=True).count()

    def get_descendants(self, include_self: bool = False) -> list:
        """Return this category and all nested descendants.

        Args:
            include_self: When True, include this category in the result.

        Returns:
            A list of :class:`Category` instances.
        """
        categories = [self] if include_self else []
        stack = list(self.children.all())
        while stack:
            node = stack.pop()
            categories.append(node)
            stack.extend(node.children.all())
        return categories

    def get_absolute_url(self) -> str:
        return reverse("catalog:category_detail", kwargs={"slug": self.slug})

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    """Product tags for filtering and search."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ProductQuerySet(models.QuerySet):
    """Custom queryset with reusable filtering/sorting helpers."""

    def active(self) -> "ProductQuerySet":
        """Return only active products."""
        return self.filter(is_active=True)

    def with_effective_price(self) -> "ProductQuerySet":
        """Annotate ``effective_price`` (sale price when set, else price).

        This lets callers filter and order by the price a shopper actually
        pays, without relying on the Python-only ``current_price`` property.
        """
        return self.annotate(
            effective_price=Coalesce("sale_price", "price", Value(Decimal("0")))
        )

    def search(self, query: str) -> "ProductQuerySet":
        """Basic keyword search across name, description, brand and SKU.

        Each whitespace-separated term must match at least one field
        (case-insensitive), which works on both SQLite and PostgreSQL.

        Args:
            query: Raw user search string.

        Returns:
            A filtered queryset.
        """
        terms = [term for term in query.split() if term]
        if not terms:
            return self
        qs = self
        for term in terms:
            qs = qs.filter(
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(sku__icontains=term)
                | Q(brand__name__icontains=term)
                | Q(category__name__icontains=term)
                | Q(tags__name__icontains=term)
            )
        return qs.distinct()


class Product(models.Model):
    """Core product model."""

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    sku = models.CharField(max_length=50, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key/value technical specifications, e.g. {\"color\": \"red\"}.",
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, related_name="products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["brand", "is_active"]),
            models.Index(fields=["price"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def current_price(self):
        """Return sale price if available, otherwise regular price."""
        return self.sale_price if self.sale_price else self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage if on sale."""
        if self.sale_price and self.price > 0:
            return round((1 - self.sale_price / self.price) * 100, 1)
        return 0

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        """True when in stock but at or below the low-stock threshold."""
        return 0 < self.stock_quantity <= self.low_stock_threshold

    @property
    def primary_image(self):
        """Return the primary image or first available."""
        return self.images.filter(is_primary=True).first() or self.images.first()

    def refresh_rating(self) -> None:
        """Recompute ``average_rating`` and ``review_count`` from reviews."""
        from django.db.models import Avg

        aggregate = self.reviews.aggregate(avg=Avg("rating"))
        self.average_rating = round(aggregate["avg"] or 0, 2)
        self.review_count = self.reviews.count()
        self.save(update_fields=["average_rating", "review_count", "updated_at"])

    def __str__(self) -> str:
        return self.name


class ProductImage(models.Model):
    """Product images with primary flag and upload validation."""

    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
            validate_image_content_type,
        ],
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "sort_order"]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"


class ProductInventory(models.Model):
    """Extended inventory tracking per product (one-to-one)."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    last_restocked = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "inventories"

    @property
    def available_quantity(self) -> int:
        """Physical stock minus reservations, never below zero."""
        return max(self.quantity - self.reserved_quantity, 0)

    @property
    def needs_reorder(self) -> bool:
        return self.available_quantity <= self.reorder_level

    def reserve(self, amount: int) -> None:
        """Reserve ``amount`` units, raising if there is not enough stock.

        Raises:
            ValueError: If ``amount`` is not positive or exceeds availability.
        """
        if amount <= 0:
            raise ValueError("Reservation amount must be positive.")
        if amount > self.available_quantity:
            raise ValueError("Not enough available stock to reserve.")
        self.reserved_quantity += amount
        self.save(update_fields=["reserved_quantity"])

    def release(self, amount: int) -> None:
        """Release a previous reservation, never dropping below zero."""
        self.reserved_quantity = max(self.reserved_quantity - amount, 0)
        self.save(update_fields=["reserved_quantity"])

    def __str__(self) -> str:
        return f"Inventory: {self.product.name}"

"""
Catalog models: Category, Product, ProductImage, Tag, Inventory.
"""

from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    """Product category with self-referential hierarchy."""

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
    image = models.ImageField(upload_to="categories/", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

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


class Product(models.Model):
    """Core product model with full-text search support."""

    category = models.ForeignKey(
        Category,
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
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, related_name="products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
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

    def __str__(self) -> str:
        return self.name


class ProductImage(models.Model):
    """Product images with primary flag for main display."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "sort_order"]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"


class ProductInventory(models.Model):
    """Extended inventory tracking per product."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    last_restocked = models.DateTimeField(null=True, blank=True)
    reorder_level = models.PositiveIntegerField(default=10)

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity

    @property
    def needs_reorder(self) -> bool:
        return self.available_quantity <= self.reorder_level

    def __str__(self) -> str:
        return f"Inventory: {self.product.name}"

"""
Test factories for the catalog app using factory_boy.

``ProductFactory`` supports a ``with_image=True`` / ``with_inventory=True``
convenience so tests can opt into related objects explicitly (avoiding
surprising extra rows).
"""

import io
from decimal import Decimal

import factory
from django.core.files.base import ContentFile
from factory.django import DjangoModelFactory

from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductInventory,
    Tag,
)


def make_test_image(color=(80, 120, 200), size=(64, 64), fmt="PNG") -> ContentFile:
    """Return an in-memory image as a ``ContentFile`` for upload in tests."""
    from PIL import Image

    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return ContentFile(buffer.getvalue(), name=f"test-image.{fmt.lower()}")


class CategoryFactory(DjangoModelFactory):
    """Factory for creating test categories."""

    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    description = "Test category description"
    is_active = True


class BrandFactory(DjangoModelFactory):
    """Factory for creating test brands."""

    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")
    is_active = True


class TagFactory(DjangoModelFactory):
    """Factory for creating test tags."""

    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"Tag {n}")


class ProductFactory(DjangoModelFactory):
    """Factory for creating test products."""

    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    slug = factory.Sequence(lambda n: f"product-{n}")
    description = "Test product description"
    price = factory.Sequence(lambda n: Decimal("10.00") + n)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    stock_quantity = 100
    specifications = factory.LazyFunction(dict)
    is_active = True

    @factory.post_generation
    def with_image(obj, create, extracted, **kwargs):
        if create and extracted:
            ProductImage.objects.create(
                product=obj,
                image=make_test_image(),
                alt_text=obj.name,
                is_primary=True,
            )

    @factory.post_generation
    def with_inventory(obj, create, extracted, **kwargs):
        if create and extracted:
            ProductInventory.objects.create(
                product=obj,
                quantity=extracted if isinstance(extracted, int) else obj.stock_quantity,
                reorder_level=kwargs.get("reorder_level", 10),
            )


class ProductImageFactory(DjangoModelFactory):
    """Factory for creating test product images with real image bytes."""

    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory, with_image=False)
    alt_text = "Test image"
    is_primary = True
    image = factory.LazyFunction(make_test_image)


class ProductInventoryFactory(DjangoModelFactory):
    """Factory for creating test inventory records."""

    class Meta:
        model = ProductInventory

    product = factory.SubFactory(ProductFactory, with_inventory=False)
    quantity = 50
    reserved_quantity = 0
    reorder_level = 10

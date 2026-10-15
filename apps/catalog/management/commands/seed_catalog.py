"""
Management command: seed the catalog with sample development data.

Creates a realistic set of categories (with subcategories), brands, tags,
products, product images (generated in-memory so no binary assets are
committed), and inventory records.

Usage:
    python manage.py seed_catalog
    python manage.py seed_catalog --flush   # wipe catalog data first
"""

import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductInventory,
    Tag,
)

CATEGORIES = [
    {
        "name": "Electronics",
        "description": "Cutting-edge gadgets and devices.",
        "children": [
            ("Smartphones", "Phones and accessories."),
            ("Laptops", "Portable computers."),
            ("Headphones", "Audio equipment."),
        ],
    },
    {
        "name": "Home & Kitchen",
        "description": "Everything for a modern home.",
        "children": [
            ("Cookware", "Pots, pans and utensils."),
            ("Small Appliances", "Coffee makers, blenders and more."),
        ],
    },
    {
        "name": "Fitness",
        "description": "Gear to keep you moving.",
        "children": [
            ("Wearables", "Fitness trackers and smart watches."),
        ],
    },
]

BRANDS = [
    ("Aurora", "Aurora makes premium consumer electronics."),
    ("Nimbus", "Nimbus builds reliable everyday devices."),
    ("Vertex", "Vertex focuses on performance hardware."),
    ("HomeCraft", "HomeCraft home and kitchen essentials."),
    ("PulseFit", "PulseFit wearable fitness technology."),
]

PRODUCTS = [
    {
        "name": "Aurora X1 Smartphone",
        "category": "Smartphones",
        "brand": "Aurora",
        "price": "899.99",
        "sale_price": "799.99",
        "stock": 42,
        "tags": ["smartphone", "5g", "flagship"],
        "description": "A flagship 5G smartphone with a 6.5-inch OLED display.",
        "specs": {
            "display": "6.5 inch OLED",
            "storage": "256 GB",
            "battery": "4500 mAh",
            "color": "Midnight Blue",
        },
        "color": (37, 99, 235),
    },
    {
        "name": "Nimbus Air Laptop 14",
        "category": "Laptops",
        "brand": "Nimbus",
        "price": "1199.00",
        "sale_price": None,
        "stock": 18,
        "tags": ["laptop", "ultrabook"],
        "description": "A lightweight 14-inch ultrabook built for all-day battery.",
        "specs": {
            "cpu": "8-core",
            "ram": "16 GB",
            "storage": "512 GB SSD",
            "weight": "1.2 kg",
        },
        "color": (16, 185, 129),
    },
    {
        "name": "Vertex Studio Headphones",
        "category": "Headphones",
        "brand": "Vertex",
        "price": "249.50",
        "sale_price": "199.00",
        "stock": 75,
        "tags": ["headphones", "noise-cancelling"],
        "description": "Over-ear headphones with active noise cancellation.",
        "specs": {
            "type": "Over-ear",
            "battery": "30 hours",
            "connectivity": "Bluetooth 5.2",
        },
        "color": (139, 92, 246),
    },
    {
        "name": "HomeCraft Stainless Cookware Set",
        "category": "Cookware",
        "brand": "HomeCraft",
        "price": "189.99",
        "sale_price": None,
        "stock": 30,
        "tags": ["cookware", "kitchen"],
        "description": "10-piece stainless steel cookware set, oven safe.",
        "specs": {"pieces": "10", "material": "Stainless steel", "oven_safe": "Yes"},
        "color": (234, 88, 12),
    },
    {
        "name": "HomeCraft Espresso Machine",
        "category": "Small Appliances",
        "brand": "HomeCraft",
        "price": "329.00",
        "sale_price": "279.00",
        "stock": 12,
        "tags": ["coffee", "espresso"],
        "description": "15-bar espresso machine with milk frother.",
        "specs": {"pressure": "15 bar", "capacity": "1.5 L", "power": "1350 W"},
        "color": (120, 53, 15),
    },
    {
        "name": "PulseFit Track 3",
        "category": "Wearables",
        "brand": "PulseFit",
        "price": "149.99",
        "sale_price": None,
        "stock": 8,
        "tags": ["fitness", "tracker"],
        "description": "Fitness tracker with heart-rate and sleep monitoring.",
        "specs": {
            "battery": "7 days",
            "water_resistance": "5 ATM",
            "display": "AMOLED",
        },
        "color": (220, 38, 38),
    },
    {
        "name": "Aurora Buds Pro",
        "category": "Headphones",
        "brand": "Aurora",
        "price": "159.99",
        "sale_price": "129.99",
        "stock": 0,
        "tags": ["earbuds", "wireless"],
        "description": "True wireless earbuds with spatial audio.",
        "specs": {"battery": "24 hours total", "water_resistance": "IPX4"},
        "color": (14, 116, 144),
    },
]

SPEC_COLORS = {
    "Aurora X1 Smartphone": (37, 99, 235),
    "Nimbus Air Laptop 14": (16, 185, 129),
}


def _placeholder_image(color=(120, 120, 120), size=(600, 600), label=""):
    """Generate a small solid-colour PNG in memory.

    Avoids committing binary assets to the repository while still giving the
    development site real, valid images.

    Args:
        color: RGB tuple for the background.
        size: (width, height) in pixels.
        label: Optional text drawn on the image.

    Returns:
        A ``ContentFile`` ready to be assigned to an ImageField.
    """
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, color)
    if label:
        draw = ImageDraw.Draw(image)
        draw.text((20, 20), label, fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    """Seed the catalog with sample development data."""

    help = "Create sample categories, brands, products, images and inventory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing catalog data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing catalog data...")
            ProductImage.objects.all().delete()
            ProductInventory.objects.all().delete()
            Product.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()

        categories = self._create_categories()
        brands = self._create_brands()
        tags = self._create_tags()
        self._create_products(categories, brands, tags)

        self.stdout.write(self.style.SUCCESS("Catalog seeded successfully."))

    def _create_categories(self) -> dict:
        """Create parent categories and subcategories. Returns {name: Category}."""
        mapping = {}
        for order, data in enumerate(CATEGORIES):
            parent, _ = Category.objects.get_or_create(
                slug=slugify(data["name"]),
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "sort_order": order,
                },
            )
            mapping[parent.name] = parent
            for child_order, (child_name, child_desc) in enumerate(data["children"]):
                child, _ = Category.objects.get_or_create(
                    slug=slugify(child_name),
                    defaults={
                        "name": child_name,
                        "description": child_desc,
                        "parent": parent,
                        "sort_order": child_order,
                    },
                )
                mapping[child.name] = child
        self.stdout.write(f"Categories ready ({len(mapping)}).")
        return mapping

    def _create_brands(self) -> dict:
        """Create brands. Returns {name: Brand}."""
        mapping = {}
        for name, description in BRANDS:
            brand, _ = Brand.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": description},
            )
            mapping[name] = brand
        self.stdout.write(f"Brands ready ({len(mapping)}).")
        return mapping

    def _create_tags(self) -> dict:
        """Create tags referenced by the sample products."""
        names = {tag for product in PRODUCTS for tag in product["tags"]}
        mapping = {}
        for name in sorted(names):
            tag, _ = Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})
            mapping[name] = tag
        self.stdout.write(f"Tags ready ({len(mapping)}).")
        return mapping

    def _create_products(self, categories, brands, tags) -> None:
        """Create sample products, their images and inventory records."""
        created = 0
        for data in PRODUCTS:
            product, was_created = Product.objects.get_or_create(
                sku=self._sku_for(data["name"]),
                defaults={
                    "name": data["name"],
                    "category": categories.get(data["category"]),
                    "brand": brands.get(data["brand"]),
                    "description": data["description"],
                    "price": Decimal(data["price"]),
                    "sale_price": (
                        Decimal(data["sale_price"]) if data["sale_price"] else None
                    ),
                    "stock_quantity": data["stock"],
                    "specifications": data["specs"],
                    "is_featured": created < 4,
                },
            )
            if not was_created:
                continue

            product.tags.set(tags[name] for name in data["tags"] if name in tags)

            if not product.images.exists():
                image = ProductImage(product=product, alt_text=product.name, is_primary=True)
                image.image.save(
                    f"{product.slug}.png",
                    _placeholder_image(color=data["color"], label=product.name),
                    save=True,
                )

            ProductInventory.objects.get_or_create(
                product=product,
                defaults={"quantity": data["stock"], "reorder_level": 10},
            )
            created += 1

        self.stdout.write(f"Products created ({created}).")

    @staticmethod
    def _sku_for(name: str) -> str:
        """Build a stable SKU from a product name."""
        return slugify(name).upper().replace("-", "")[:20]

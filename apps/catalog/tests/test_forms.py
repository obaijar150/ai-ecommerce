"""
Tests for catalog forms: ProductForm, CategoryForm, ProductImageForm.
"""

from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .factories import CategoryFactory, ProductFactory, make_test_image
from apps.catalog.forms import CategoryForm, ProductForm, ProductImageForm


class TestProductForm(TestCase):
    """Test ProductForm validation and cleaning."""

    def _valid_data(self, **overrides):
        data = {
            "name": "New Product",
            "description": "A description",
            "price": "19.99",
            "sale_price": "",
            "sku": "new-sku-1",
            "stock_quantity": 10,
            "low_stock_threshold": 5,
            "specifications": '{"color": "red"}',
            "is_active": True,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        """A correctly filled form is valid and uppercases the SKU."""
        form = ProductForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["sku"], "NEW-SKU-1")
        self.assertEqual(form.cleaned_data["specifications"], {"color": "red"})

    def test_duplicate_sku_rejected_case_insensitive(self):
        """A duplicate SKU (any case) is rejected."""
        ProductFactory(sku="DUP-1")
        form = ProductForm(data=self._valid_data(sku="dup-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("sku", form.errors)

    def test_duplicate_sku_allowed_when_editing_self(self):
        """A product may keep its own SKU when edited."""
        product = ProductFactory(sku="KEEP-1")
        form = ProductForm(data=self._valid_data(sku="KEEP-1"), instance=product)
        self.assertTrue(form.is_valid(), form.errors)

    def test_price_must_be_positive(self):
        """A zero or negative price is rejected."""
        form = ProductForm(data=self._valid_data(price="0"))
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_sale_price_must_be_less_than_price(self):
        """Sale price greater than or equal to price is rejected."""
        form = ProductForm(data=self._valid_data(price="20", sale_price="25"))
        self.assertFalse(form.is_valid())
        self.assertIn("sale_price", form.errors)

    def test_invalid_specifications_json(self):
        """Malformed JSON in specifications is rejected."""
        form = ProductForm(data=self._valid_data(specifications="{not json}"))
        self.assertFalse(form.is_valid())
        self.assertIn("specifications", form.errors)

    def test_non_object_specifications_rejected(self):
        """A JSON array is not a valid specifications object."""
        form = ProductForm(data=self._valid_data(specifications="[1, 2, 3]"))
        self.assertFalse(form.is_valid())
        self.assertIn("specifications", form.errors)

    def test_blank_specifications_defaults_to_empty_dict(self):
        """Blank specifications become an empty dict."""
        form = ProductForm(data=self._valid_data(specifications=""))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["specifications"], {})

    def test_stock_cannot_be_negative(self):
        """Negative stock is rejected by the field."""
        form = ProductForm(data=self._valid_data(stock_quantity=-5))
        self.assertFalse(form.is_valid())
        self.assertIn("stock_quantity", form.errors)


class TestCategoryForm(TestCase):
    """Test CategoryForm validation."""

    def test_valid_category_form(self):
        """A minimal category form is valid."""
        form = CategoryForm(data={"name": "Toys", "is_active": True, "sort_order": 0})
        self.assertTrue(form.is_valid(), form.errors)

    def test_category_cannot_be_own_parent(self):
        """A category cannot be set as its own parent."""
        category = CategoryFactory()
        form = CategoryForm(
            data={"name": category.name, "parent": category.pk, "sort_order": 0},
            instance=category,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)


class TestProductImageForm(TestCase):
    """Test ProductImageForm and upload validation."""

    def test_valid_image(self):
        """A valid png upload is accepted."""
        upload = SimpleUploadedFile(
            "pic.png", make_test_image().read(), content_type="image/png"
        )
        form = ProductImageForm(
            data={"alt_text": "pic", "is_primary": True, "sort_order": 0},
            files={"image": upload},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_disallowed_extension_rejected(self):
        """A .gif upload is rejected by the extension validator."""
        upload = SimpleUploadedFile("bad.gif", b"GIF89a", content_type="image/gif")
        form = ProductImageForm(
            data={"alt_text": "bad", "sort_order": 0}, files={"image": upload}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

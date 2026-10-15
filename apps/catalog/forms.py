"""
Catalog forms: product, image, category, and brand management.

These forms are used by the Django admin (and can be reused by any future
staff-facing CRUD views). Validation lives here so it applies everywhere the
form is used.
"""

import json

from django import forms

from .models import Brand, Category, Product, ProductImage


class ProductForm(forms.ModelForm):
    """Form for creating and editing products with business validation."""

    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "category",
            "brand",
            "tags",
            "price",
            "sale_price",
            "sku",
            "stock_quantity",
            "low_stock_threshold",
            "weight_kg",
            "specifications",
            "is_active",
            "is_featured",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "specifications": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": '{"color": "red", "size": "L"}',
                }
            ),
        }

    def clean_sku(self) -> str:
        """Normalise and validate SKU uniqueness (case-insensitive)."""
        sku = self.cleaned_data["sku"].strip().upper()
        queryset = Product.objects.filter(sku__iexact=sku)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("A product with this SKU already exists.")
        return sku

    def clean_price(self):
        """Validate price is positive."""
        price = self.cleaned_data["price"]
        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean_sale_price(self):
        """Validate sale price is less than the regular price."""
        sale_price = self.cleaned_data.get("sale_price")
        price = self.cleaned_data.get("price")
        if sale_price is not None and sale_price <= 0:
            raise forms.ValidationError("Sale price must be greater than zero.")
        if sale_price and price and sale_price >= price:
            raise forms.ValidationError("Sale price must be less than the regular price.")
        return sale_price

    def clean_specifications(self) -> dict:
        """Ensure specifications resolve to a JSON object."""
        specs = self.cleaned_data.get("specifications")
        if not specs:
            return {}
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except (TypeError, ValueError):
                raise forms.ValidationError("Specifications must be valid JSON.")
        if not isinstance(specs, dict):
            raise forms.ValidationError("Specifications must be a JSON object.")
        return specs


class ProductImageForm(forms.ModelForm):
    """Form for uploading product images (applies model validators)."""

    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "is_primary", "sort_order"]


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories and subcategories."""

    class Meta:
        model = Category
        fields = ["name", "description", "parent", "image", "is_active", "sort_order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_parent(self):
        """Prevent a category from being its own parent."""
        parent = self.cleaned_data.get("parent")
        if parent and self.instance.pk and parent.pk == self.instance.pk:
            raise forms.ValidationError("A category cannot be its own parent.")
        return parent


class BrandForm(forms.ModelForm):
    """Form for creating and editing brands."""

    class Meta:
        model = Brand
        fields = ["name", "description", "website", "logo", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

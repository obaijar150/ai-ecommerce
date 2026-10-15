"""
Orders forms: add to cart, update cart, and checkout.

Checkout deliberately accepts only an opaque payment *token*, never card
numbers or CVV values.
"""

from __future__ import annotations

import re

from django import forms

from apps.accounts.models import Address

from .models import Order

# A mock token such as ``tok_success`` / ``tok_failure`` is allowed. Anything
# that looks like a card number (a long run of digits) is rejected outright.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-]{0,64}$")
_CARD_NUMBER_RE = re.compile(r"^\d{12,19}$")


class AddToCartForm(forms.Form):
    """Validate a quantity when adding a product to the cart."""

    quantity = forms.IntegerField(min_value=1, max_value=999, initial=1)

    def clean_quantity(self) -> int:
        quantity = self.cleaned_data["quantity"]
        if quantity < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return quantity


class CartUpdateForm(forms.Form):
    """Validate a new quantity for a cart line (0 removes the line)."""

    quantity = forms.IntegerField(min_value=0, max_value=999)

    def clean_quantity(self) -> int:
        quantity = self.cleaned_data["quantity"]
        if quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity


class CheckoutForm(forms.Form):
    """Collect a shipping address and payment method for checkout.

    Provides the user's saved addresses plus inline fields to create a new one.
    The payment section only accepts an optional opaque token; card numbers are
    explicitly rejected.
    """

    address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        required=False,
        empty_label="— Use a new address —",
        label="Saved address",
    )

    # New-address fields (used when no saved address is selected).
    label = forms.CharField(max_length=50, required=False, initial="Home")
    street = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    postal_code = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=100, required=False, initial="United States")

    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        initial=Order.PaymentMethod.MOCK_CARD,
    )
    payment_token = forms.CharField(
        max_length=64,
        required=False,
        help_text=(
            "Development only. Use 'tok_success' to approve or 'tok_failure' to "
            "simulate a declined payment. Never enter real card details."
        ),
    )
    idempotency_key = forms.CharField(
        max_length=64, required=False, widget=forms.HiddenInput
    )

    def __init__(self, *args, user=None, **kwargs):
        """Limit the saved-address choices to the given user's addresses."""
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and user.is_authenticated:
            self.fields["address"].queryset = Address.objects.filter(
                user=user
            ).order_by("-is_default", "label")

    def clean_payment_token(self) -> str:
        """Reject anything that looks like a card number or CVV."""
        token = (self.cleaned_data.get("payment_token") or "").strip()
        if not token:
            return ""
        if _CARD_NUMBER_RE.match(token):
            raise forms.ValidationError(
                "Do not enter card numbers. Use a mock token such as "
                "'tok_success' or 'tok_failure'."
            )
        if not _TOKEN_RE.match(token):
            raise forms.ValidationError("Payment token contains invalid characters.")
        return token

    def clean(self) -> dict:
        """Require a saved address or a complete new address."""
        cleaned = super().clean()
        if not cleaned.get("address"):
            required = ["street", "city", "state", "postal_code", "country"]
            if any(not cleaned.get(field) for field in required):
                raise forms.ValidationError(
                    "Please choose a saved address or complete all new-address fields."
                )
        return cleaned

    def get_shipping_address(self) -> Address:
        """Return the chosen address, creating a new one if necessary.

        Must be called only after :meth:`clean` has passed.
        """
        address = self.cleaned_data.get("address")
        if address is not None:
            return address

        is_first = not Address.objects.filter(user=self.user).exists()
        return Address.objects.create(
            user=self.user,
            label=self.cleaned_data.get("label") or "Home",
            street=self.cleaned_data["street"],
            city=self.cleaned_data["city"],
            state=self.cleaned_data["state"],
            postal_code=self.cleaned_data["postal_code"],
            country=self.cleaned_data["country"],
            is_default=is_first,
        )

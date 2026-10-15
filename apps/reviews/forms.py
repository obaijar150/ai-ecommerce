"""
Reviews forms.
"""

from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    """Review creation form."""

    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "rating": forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            "title": forms.TextInput(attrs={"placeholder": "Summary of your review"}),
            "body": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Share your experience..."}
            ),
        }

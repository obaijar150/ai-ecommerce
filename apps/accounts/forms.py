"""
Accounts forms: registration, login, profile, address, password reset.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Address, Profile

User = get_user_model()


class CustomUserCreationForm(forms.ModelForm):
    """Extended user registration form with email and validation."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Create a strong password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat your password"}),
    )

    class Meta:
        model = User
        fields = ("username", "email")
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Choose a username"}),
        }

    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password2(self):
        """Validate password confirmation matches."""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        """Save user with hashed password. Profile is auto-created by signal."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with styled widgets."""

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"placeholder": "Username or email", "autofocus": True}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )


class ProfileForm(forms.ModelForm):
    """Profile edit form."""

    class Meta:
        model = Profile
        fields = ("phone", "avatar", "bio", "date_of_birth", "newsletter_subscribed")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell us about yourself..."}),
            "phone": forms.TextInput(attrs={"placeholder": "+1 234 567 8900"}),
        }


class AddressForm(forms.ModelForm):
    """Address create/edit form."""

    class Meta:
        model = Address
        fields = ("label", "street", "city", "state", "postal_code", "country", "is_default")
        widgets = {
            "label": forms.TextInput(attrs={"placeholder": "Home, Work, etc."}),
            "street": forms.TextInput(attrs={"placeholder": "123 Main St"}),
            "city": forms.TextInput(attrs={"placeholder": "City"}),
            "state": forms.TextInput(attrs={"placeholder": "State/Province"}),
            "postal_code": forms.TextInput(attrs={"placeholder": "12345"}),
            "country": forms.TextInput(attrs={"placeholder": "Country"}),
        }


class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com", "autofocus": True})
    )

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """Send password reset email with custom template."""
        subject = render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = render_to_string(email_template_name, context)

        send_mail(
            subject,
            body,
            from_email,
            [to_email],
            html_message=render_to_string("emails/password_reset.html", context),
            fail_silently=False,
        )


class CustomSetPasswordForm(SetPasswordForm):
    """Custom password reset confirmation form."""

    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"placeholder": "New password", "autofocus": True}),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password"}),
    )

"""
Accounts views: registration, login, logout, profile, addresses, wishlist, password reset.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import (
    AddressForm,
    CustomAuthenticationForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    CustomUserCreationForm,
    ProfileForm,
)
from .models import Address, Profile, WishlistItem

User = get_user_model()


class RegisterView(CreateView):
    """User registration view with automatic profile creation."""

    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("catalog:home")

    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users away from registration."""
        if request.user.is_authenticated:
            return redirect("catalog:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f"Welcome, {self.object.username}! Your account has been created.",
        )
        return response


class CustomLoginView(LoginView):
    """Custom login view."""

    form_class = CustomAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Custom logout view — supports both GET and POST for compatibility."""

    next_page = reverse_lazy("catalog:home")

    def dispatch(self, request, *args, **kwargs):
        """Allow GET requests for logout (Django 5.2 defaults to POST only)."""
        messages.info(request, "You have been logged out.")
        if request.method == "GET":
            return self.post(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


# ── Password Reset Views ─────────────────────────────────────


class CustomPasswordResetView(PasswordResetView):
    """Password reset request view."""

    template_name = "accounts/password_reset.html"
    form_class = CustomPasswordResetForm
    email_template_name = "emails/password_reset.html"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Password reset email sent confirmation."""

    template_name = "accounts/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Password reset confirmation (new password entry)."""

    template_name = "accounts/password_reset_confirm.html"
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Password reset success page."""

    template_name = "accounts/password_reset_complete.html"


# ── Profile & Account Views ──────────────────────────────────


class ProfileView(DetailView):
    """User profile detail view — owner or staff only."""

    model = Profile
    template_name = "accounts/profile.html"
    context_object_name = "profile"

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return Profile.objects.get(user=self.request.user)

    def get(self, request, *args, **kwargs):
        """Ensure users can only view their own profile."""
        profile = self.get_object()
        if profile.user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("You can only view your own profile.")
        return super().get(request, *args, **kwargs)


class ProfileUpdateView(UpdateView):
    """User profile edit view — owner or staff only."""

    model = Profile
    form_class = ProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return Profile.objects.get(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)


# ── Address Views ────────────────────────────────────────────


class AddressListView(ListView):
    """List user addresses — owner only."""

    model = Address
    template_name = "accounts/result_list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        return super().get(request, *args, **kwargs)


class AddressCreateView(CreateView):
    """Create a new address — authenticated users only."""

    model = Address
    form_class = AddressForm
    template_name = "accounts/form.html"
    success_url = reverse_lazy("accounts:address_list")

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user

        # If this is the only address, make it default
        if not Address.objects.filter(user=self.request.user).exists():
            form.instance.is_default = True

        messages.success(self.request, "Address added successfully.")
        return super().form_valid(form)


class AddressUpdateView(UpdateView):
    """Edit an existing address — owner only."""

    model = Address
    form_class = AddressForm
    template_name = "accounts/form.html"
    success_url = reverse_lazy("accounts:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Address updated successfully.")
        return super().form_valid(form)


class AddressDeleteView(UpdateView):
    """Delete an address — owner only."""

    model = Address
    template_name = "accounts/address_confirm_delete.html"
    success_url = reverse_lazy("accounts:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Address deleted.")
        return super().form_valid(form)


# ── Wishlist Views ───────────────────────────────────────────


class WishlistView(LoginRequiredMixin, ListView):
    """User wishlist page — authenticated users only."""

    model = WishlistItem
    template_name = "accounts/wishlist.html"
    context_object_name = "wishlist_items"

    def get_queryset(self):
        return WishlistItem.objects.filter(user=self.request.user).select_related(
            "product"
        )


# ── Staff-Only Views ─────────────────────────────────────────


class StaffRequiredMixin:
    """Mixin to restrict views to staff/admin users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden(
                "You do not have permission to access this page."
            )
        return super().dispatch(request, *args, **kwargs)


@login_required
def admin_dashboard_redirect(request):
    """Redirect staff to admin panel, show forbidden for regular users."""
    if request.user.is_staff:
        return redirect("/admin/")
    return HttpResponseForbidden(
        "You do not have permission to access the admin dashboard."
    )

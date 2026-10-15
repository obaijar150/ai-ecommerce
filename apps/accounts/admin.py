"""
Django admin configuration for accounts app.
"""

from django.contrib import admin

from .models import Address, Profile, WishlistItem


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "newsletter_subscribed", "created_at"]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "city", "country", "is_default"]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "added_at"]

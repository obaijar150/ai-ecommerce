from django.apps import AppConfig


class SearchConfig(AppConfig):
    """Configuration for the search app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Product Search"

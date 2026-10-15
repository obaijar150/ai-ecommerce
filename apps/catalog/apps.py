from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Configuration for the catalog app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    verbose_name = "Product Catalog"

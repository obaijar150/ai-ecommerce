from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the accounts app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "User Accounts"

    def ready(self):
        """Import signals when the app is ready."""
        import apps.accounts.signals  # noqa: F401

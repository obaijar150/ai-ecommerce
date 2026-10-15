"""
Development settings — overrides base.py for local development.
Uses SQLite by default. To use PostgreSQL, start Docker Compose first.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

# Use SQLite for quick local development (no PostgreSQL required)
# To use PostgreSQL: docker-compose up -d db redis
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

ALLOWED_HOSTS = ["*"]

# Email to console for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Debug toolbar is optional in development
# Install with: pip install django-debug-toolbar
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE = MIDDLEWARE + ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Disable security features for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Logging: everything to console
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405

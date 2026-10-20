"""
Development settings — overrides base.py for local development.

PostgreSQL is the default database (start it with ``docker compose up -d db``).
Set ``USE_SQLITE=1`` only for a quick offline fallback; tests and the project
are validated against PostgreSQL.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

# PostgreSQL comes from base.py. Opt into SQLite explicitly when needed.
if env.bool("USE_SQLITE", default=False):  # noqa: F405
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

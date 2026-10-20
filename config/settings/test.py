"""
Test settings — isolated, no external cache/broker.

Tests run against PostgreSQL by default so we exercise the same database
dialect as production. Set ``USE_SQLITE=1`` for a quick offline run.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "*"]

# PostgreSQL comes from base.py (Django creates a ``test_`` database).
if env.bool("USE_SQLITE", default=False):  # noqa: F405
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }

# Use in-memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Fast password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable Celery for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable security for test speed
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging: minimal
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
}

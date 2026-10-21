"""
Base Django settings for AI E-Commerce Platform.

This file contains shared configuration for all environments.
Environment-specific overrides go in dev.py, production.py, or test.py.
"""

from pathlib import Path

import environ

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment helper
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    LOG_LEVEL=(str, "INFO"),
    LOG_FILE=(str, "logs/django.log"),
    AI_RECOMMENDATION_TRAINING_INTERVAL_HOURS=(int, 6),
    AI_CHATBOT_MODEL_PATH=(str, "models/chatbot_classifier.pkl"),
    AI_NLP_MODEL_NAME=(str, "distilbart-cnn-12-6"),
    AI_SUMMARY_MAX_LENGTH=(int, 150),
    MAX_UPLOAD_SIZE_MB=(int, 5),
    ALLOWED_IMAGE_TYPES=(list, ["jpg", "jpeg", "png", "webp"]),
    PAYMENT_PROVIDER=(str, "mock"),
    MOCK_PAYMENT_FAILURE_RATE=(float, 0.0),
    FREE_SHIPPING_THRESHOLD=(str, "50.00"),
    SHIPPING_FLAT_RATE=(str, "5.99"),
    SALES_TAX_RATE=(str, "0.08"),
)

# Load .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# ── Core Django ───────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    # Django built-in
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.postgres",

    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "csp",
    "django_celery_beat",
    "drf_spectacular",

    # Local apps
    "apps.accounts",
    "apps.catalog",
    "apps.orders",
    "apps.reviews",
    "apps.search",
    "apps.ai_engine",
    "apps.analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.orders.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database (PostgreSQL) ─────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="ecommerce"),
        "USER": env("DB_USER", default="ecommerce_user"),
        "PASSWORD": env("DB_PASSWORD", default="change-me"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

# ── Password Validation ──────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Password Hashing (Argon2 — most secure) ──────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# ── Internationalization ──────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static Files ─────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ── Media Files ──────────────────────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
MAX_UPLOAD_SIZE_MB = env("MAX_UPLOAD_SIZE_MB")
ALLOWED_IMAGE_TYPES = env("ALLOWED_IMAGE_TYPES")

# ── Default Primary Key ──────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Django REST Framework ────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}

# ── CORS ─────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# ── Content Security Policy ──────────────────────────────────
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")

# ── Email ────────────────────────────────────────────────────
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# ── Celery ───────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# ── Redis Cache ──────────────────────────────────────────────
# Redis is optional: if it is unavailable the backend transparently falls
# back to an in-process cache so API throttling never turns into a 500.
CACHES = {
    "default": {
        "BACKEND": "config.cache.ResilientRedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "TIMEOUT": 300,
        "OPTIONS": {
            "db": "0",
        },
    }
}

# ── Logging ──────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / env("LOG_FILE", default="logs/django.log"),
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": env("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps.ai_engine": {
            "handlers": ["console", "file"],
            "level": env("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}

# ── AI Engine Settings ───────────────────────────────────────
AI_RECOMMENDATION_TRAINING_INTERVAL_HOURS = env("AI_RECOMMENDATION_TRAINING_INTERVAL_HOURS")
AI_CHATBOT_MODEL_PATH = BASE_DIR / env("AI_CHATBOT_MODEL_PATH", default="models/chatbot_classifier.pkl")
AI_NLP_MODEL_NAME = env("AI_NLP_MODEL_NAME", default="distilbart-cnn-12-6")
AI_SUMMARY_MAX_LENGTH = env("AI_SUMMARY_MAX_LENGTH", default=150)

# Artifacts (trained models / embedding indexes) live outside version control.
AI_ARTIFACTS_DIR = BASE_DIR / env("AI_ARTIFACTS_DIR", default="ai_artifacts")
# Embedding backend: "tfidf" (deterministic, always available) or the optional
# "sentence-transformers" pretrained model (needs PyTorch; falls back offline).
AI_EMBEDDING_BACKEND = env("AI_EMBEDDING_BACKEND", default="tfidf")
AI_EMBEDDING_MODEL_NAME = env(
    "AI_EMBEDDING_MODEL_NAME", default="sentence-transformers/all-MiniLM-L6-v2"
)
# Optional local LLM runtime (Ollama). Disabled by default; never cloud inference.
AI_LLM_ENABLED = env("AI_LLM_ENABLED", default="false").lower() in {"1", "true", "yes"}
AI_LLM_BACKEND = env("AI_LLM_BACKEND", default="ollama")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://localhost:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", default="qwen2.5:0.5b")


# ── Payments & Pricing ───────────────────────────────────────
# Only free/mock providers are supported. No real card data is ever stored.
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER")
MOCK_PAYMENT_FAILURE_RATE = env("MOCK_PAYMENT_FAILURE_RATE")
FREE_SHIPPING_THRESHOLD = env("FREE_SHIPPING_THRESHOLD")
SHIPPING_FLAT_RATE = env("SHIPPING_FLAT_RATE")
SALES_TAX_RATE = env("SALES_TAX_RATE")

# ── Security (override in production.py) ─────────────────────
SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

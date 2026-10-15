"""
Celery configuration for AI E-Commerce Platform.

Handles async tasks: AI model training, email sending, review summarization.
"""

from celery import Celery
from django.conf import settings

# Set the default Django settings module
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")

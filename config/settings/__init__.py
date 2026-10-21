"""
Default settings entry point.

``config.settings`` is the module Django loads when no
``DJANGO_SETTINGS_MODULE`` is exported (``manage.py`` and ``wsgi.py`` both
default to it). Importing the development configuration here keeps
``python manage.py runserver`` working out of the box, while the
environment-specific modules remain available and explicit:

* ``config.settings.dev``        — local development (PostgreSQL via Docker)
* ``config.settings.test``       — automated test suite
* ``config.settings.production`` — hardened production settings

Production deployments must set ``DJANGO_SETTINGS_MODULE=config.settings.production``
(Dockerfile and the deployment docs already do this) and must never rely on
this default.
"""

from .dev import *  # noqa: F401,F403

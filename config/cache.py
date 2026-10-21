"""
Resilient cache backends.

The default cache is Redis (shared between the web workers, Celery and the
rate limiter). Redis is *optional* infrastructure in this project: a developer
running only PostgreSQL should still get a working site.

:class:`ResilientRedisCache` transparently falls back to an in-process
``LocMemCache`` whenever Redis is unreachable, so a cache outage degrades
performance instead of returning HTTP 500 on every API request (the DRF
throttling classes read the cache on each request).

Only the read/write path is patched; cache key semantics are unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger(__name__)


class ResilientRedisCache(RedisCache):
    """Redis cache that falls back to a local memory cache when unavailable."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._fallback: LocMemCache | None = None

    def _get_fallback(self) -> LocMemCache:
        """Return (and lazily build) the in-process fallback cache."""
        if self._fallback is None:
            self._fallback = LocMemCache(
                "fallback", {"LOCATION": "resilient-redis-fallback"}
            )
        return self._fallback

    def _use_fallback(self, operation: str, error: Exception) -> None:
        """Log a cache failure once per outage without breaking the request."""
        logger.warning(
            "Cache operation '%s' failed (%s); using in-process fallback cache.",
            operation,
            error.__class__.__name__,
        )

    def get(self, key: str, default: Any = None, version: Any = None) -> Any:
        """Return the cached value, falling back to the local cache on error."""
        try:
            return super().get(key, default, version)
        except Exception as error:  # noqa: BLE001 - never break the request
            self._use_fallback("get", error)
            return self._get_fallback().get(key, default, version)

    def set(self, key: str, value: Any, timeout: Any = None, version: Any = None) -> None:
        """Store a value in Redis, falling back to the local cache on error."""
        try:
            super().set(key, value, timeout, version)
        except Exception as error:  # noqa: BLE001 - never break the request
            self._use_fallback("set", error)
            self._get_fallback().set(key, value, timeout, version)

    def delete(self, key: str, version: Any = None) -> None:
        """Delete a key, falling back to the local cache on error."""
        try:
            super().delete(key, version)
        except Exception as error:  # noqa: BLE001 - never break the request
            self._use_fallback("delete", error)
            self._get_fallback().delete(key, version)

    def incr(self, key: str, delta: int = 1, version: Any = None) -> int:
        """Increment a counter, falling back to the local cache on error."""
        try:
            return super().incr(key, delta, version)
        except Exception as error:  # noqa: BLE001 - never break the request
            self._use_fallback("incr", error)
            fallback = self._get_fallback()
            try:
                return fallback.incr(key, delta, version)
            except ValueError:
                # Redis creates a missing counter with the delta as its value,
                # while LocMem raises. Mirror the Redis behaviour.
                fallback.set(key, delta, version=version)
                return delta

    def clear(self) -> None:
        """Clear the cache, including the fallback."""
        try:
            super().clear()
        except Exception as error:  # noqa: BLE001 - never break the request
            self._use_fallback("clear", error)
        if self._fallback is not None:
            self._fallback.clear()

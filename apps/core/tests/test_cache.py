"""
Tests for the resilient cache backend.

Redis is optional infrastructure: when it is unreachable the cache must
degrade to an in-process fallback instead of raising, because the DRF
throttling classes read the cache on every API request.
"""

from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from config.cache import ResilientRedisCache


class TestResilientRedisCache(TestCase):
    """The cache must never propagate a Redis connection error."""

    def _cache_with_failing_redis(self) -> ResilientRedisCache:
        """Build a cache instance whose Redis client always fails."""
        failing = ResilientRedisCache(
            "default", {"LOCATION": "redis://localhost:6379/0"}
        )
        failing._cache = mock.MagicMock()
        failing._cache.get.side_effect = ConnectionError("redis is down")
        failing._cache.set.side_effect = ConnectionError("redis is down")
        failing._cache.delete.side_effect = ConnectionError("redis is down")
        failing._cache.incr.side_effect = ConnectionError("redis is down")
        failing._cache.clear.side_effect = ConnectionError("redis is down")
        return failing

    def test_get_falls_back_when_redis_unavailable(self):
        """A failed Redis read returns the default instead of raising."""
        failing = self._cache_with_failing_redis()
        self.assertEqual(failing.get("missing-key", "fallback-value"), "fallback-value")

    def test_set_falls_back_when_redis_unavailable(self):
        """A failed Redis write is stored in the fallback cache instead."""
        failing = self._cache_with_failing_redis()
        failing.set("key", "value")
        self.assertEqual(failing.get("key"), "value")

    def test_delete_falls_back_when_redis_unavailable(self):
        """A failed Redis delete is handled without raising."""
        failing = self._cache_with_failing_redis()
        failing.set("key", "value")
        failing.delete("key")
        self.assertIsNone(failing.get("key"))

    def test_incr_falls_back_when_redis_unavailable(self):
        """A failed Redis increment is served by the fallback cache."""
        failing = self._cache_with_failing_redis()
        self.assertEqual(failing.incr("counter", 1), 1)

    def test_clear_falls_back_when_redis_unavailable(self):
        """A failed Redis clear does not raise."""
        failing = self._cache_with_failing_redis()
        failing.clear()

    def test_default_cache_backend_is_resilient(self):
        """The project cache is configured with the resilient backend.

        The test settings deliberately swap in a local-memory cache for
        isolation, so the assertion is made against the shipped base
        configuration that dev/production actually use.
        """
        from config.settings import base

        self.assertIn(
            "ResilientRedisCache",
            base.CACHES["default"]["BACKEND"],
        )

    def test_regular_operations_still_work(self):
        """Normal get/set/delete behave normally when Redis is healthy."""
        cache.set("audit-key", "audit-value")
        self.assertEqual(cache.get("audit-key"), "audit-value")
        cache.delete("audit-key")
        self.assertIsNone(cache.get("audit-key"))

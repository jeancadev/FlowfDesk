"""
Redis Cache Adapter — Implementation of CachePort.

Provides caching for sessions, rate limiting counters,
and frequently-accessed ticket data.
"""

from __future__ import annotations

import redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis implementation of the CachePort interface."""

    def __init__(self, url: str | None = None):
        settings = get_settings()
        self._client = redis.from_url(
            url or settings.REDIS_URL,
            decode_responses=True,
        )

    def get(self, key: str) -> str | None:
        """Retrieve a value from cache."""
        try:
            return self._client.get(key)
        except redis.ConnectionError:
            logger.warning("redis_connection_error", operation="get", key=key)
            return None

    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        """Store a value in cache with TTL."""
        try:
            self._client.setex(key, ttl_seconds, value)
        except redis.ConnectionError:
            logger.warning("redis_connection_error", operation="set", key=key)

    def delete(self, key: str) -> None:
        """Remove a value from cache."""
        try:
            self._client.delete(key)
        except redis.ConnectionError:
            logger.warning("redis_connection_error", operation="delete", key=key)

    def increment(self, key: str, ttl_seconds: int = 60) -> int:
        """Increment a counter (for rate limiting). Returns the new count."""
        try:
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            results = pipe.execute()
            return results[0]  # The incremented value
        except redis.ConnectionError:
            logger.warning("redis_connection_error", operation="increment", key=key)
            return 0

    def ping(self) -> bool:
        """Health check for Redis connection."""
        try:
            return self._client.ping()
        except redis.ConnectionError:
            return False

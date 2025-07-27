"""Redis/Valkey cache client.

This module provides a simple interface to the cache.  It hides the details
of connection pooling and allows setting and getting values with TTLs.  The
underlying client can connect to Redis or Valkey interchangeably.
"""
from __future__ import annotations

import logging
from typing import Optional, Any

import redis

from .config import get_settings

logger = logging.getLogger(__name__)


class Cache:
    """Cache wrapper providing simple get/set operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = redis.Redis(host=settings.cache_host, port=settings.cache_port)
        try:
            # Test the connection
            self._client.ping()
            logger.info("Connected to cache at %s:%s", settings.cache_host, settings.cache_port)
        except redis.ConnectionError as exc:
            logger.error("Failed to connect to cache: %s", exc)
            raise

    def get(self, key: str) -> Optional[str]:
        value = self._client.get(key)
        return value.decode("utf-8") if value is not None else None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        # Set value with TTL in seconds
        self._client.set(name=key, value=value, ex=ttl)

    def delete(self, key: str) -> None:
        self._client.delete(key)


_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Return a singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache

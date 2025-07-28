import aioredis
from typing import Any, Optional
from .config import settings


async def get_cache() -> aioredis.Redis:
    """Create a Redis connection using the configured URL."""
    return await aioredis.from_url(settings.redis_url, decode_responses=True)


async def ping() -> bool:
    """Check if the cache is reachable."""
    cache = await get_cache()
    try:
        return await cache.ping()
    finally:
        await cache.close()


async def set_value(key: str, value: Any, expire: Optional[int] = None) -> None:
    """Set a value in the cache with an optional expiration time."""
    cache = await get_cache()
    try:
        await cache.set(key, value, ex=expire)
    finally:
        await cache.close()


async def get_value(key: str) -> Optional[str]:
    """Retrieve a value from the cache, returning None if missing."""
    cache = await get_cache()
    try:
        return await cache.get(key)
    finally:
        await cache.close()

"""Simple in-memory cache for Basketball Stats Tracker."""

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry["expires_at"]:
                    logger.debug(f"Cache HIT for key: {key}")
                    return entry["value"]
                else:
                    # Expired, remove it
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED for key: {key}")

            logger.debug(f"Cache MISS for key: {key}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set value in cache with TTL."""
        async with self._lock:
            self._cache[key] = {"value": value, "expires_at": time.time() + ttl_seconds, "created_at": time.time()}
            logger.debug(f"Cache SET for key: {key}, TTL: {ttl_seconds}s")

    async def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern or all if no pattern."""
        async with self._lock:
            if pattern is None:
                # Clear all cache
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cache cleared: {count} entries removed")
            else:
                # Clear entries matching pattern
                keys_to_remove = [k for k in self._cache if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(f"Cache invalidated: {len(keys_to_remove)} entries matching '{pattern}' removed")

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            now = time.time()
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if now >= entry["expires_at"])
            active_entries = total_entries - expired_entries

            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
            }


# Global cache instance
cache = SimpleCache()


def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and auth context
            auth_context = kwargs.get("auth_context", {})
            user_role = auth_context.get("user_role", "anonymous")
            is_authenticated = auth_context.get("is_authenticated", False)

            # Cache key includes auth status to serve different content to logged-in users
            cache_key = f"{key_prefix}{func.__name__}:{user_role}:{is_authenticated}"

            # Try to get from cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Cache miss - call the original function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


# Cache invalidation helper
async def invalidate_all_cache():
    """Invalidate all cache entries (e.g., after data updates)."""
    await cache.invalidate()
    logger.info("All cache entries invalidated")


async def get_cache_stats():
    """Get cache statistics for monitoring."""
    return await cache.get_stats()


def invalidate_cache_after(func: Callable) -> Callable:
    """Decorator to invalidate cache after function execution (for data modification endpoints)."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Execute the original function first
        result = await func(*args, **kwargs)

        # If the function completed successfully, invalidate cache
        # Only invalidate if the result indicates success
        if isinstance(result, dict) and result.get("success") is not False:
            await invalidate_all_cache()
            logger.info(f"Cache auto-invalidated after {func.__name__}")
        elif not isinstance(result, dict):
            # For non-dict responses (like HTML), always invalidate
            await invalidate_all_cache()
            logger.info(f"Cache auto-invalidated after {func.__name__}")

        return result

    return wrapper

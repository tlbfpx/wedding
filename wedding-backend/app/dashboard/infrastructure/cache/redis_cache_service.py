"""Redis cache service for dashboard."""
from __future__ import annotations
import json
from typing import Optional, Any
from decimal import Decimal

from app.utils.cache import redis_client


class RedisCacheService:
    """Redis cache service for dashboard data."""

    @staticmethod
    async def get(cache_key: str) -> Optional[dict]:
        """Get cached data.

        Args:
            cache_key: Cache key

        Returns:
            Cached data as dict, or None if not found
        """
        cached = await redis_client.get(cache_key)
        if not cached:
            return None

        if cached == "NULL":
            # Cache penetration protection
            return None

        try:
            return json.loads(cached)
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    async def set(cache_key: str, data: Any, ttl: int = 300) -> None:
        """Set cache data.

        Args:
            cache_key: Cache key
            data: Data to cache (will be JSON serialized)
            ttl: Time to live in seconds (default 300)
        """
        # Convert Decimal to float for JSON serialization
        json_data = json.dumps(data, default=lambda o: float(o) if isinstance(o, Decimal) else str(o))
        await redis_client.setex(cache_key, ttl, json_data)

    @staticmethod
    async def delete(cache_key: str) -> None:
        """Delete cache key.

        Args:
            cache_key: Cache key to delete
        """
        await redis_client.delete(cache_key)

    @staticmethod
    async def delete_pattern(pattern: str) -> None:
        """Delete cache keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "dashboard:health:*")
        """
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await redis_client.delete(*keys)

    @staticmethod
    async def set_null(cache_key: str, ttl: int = 30) -> None:
        """Set null value for cache penetration protection.

        Args:
            cache_key: Cache key
            ttl: Time to live (default 30s for null values)
        """
        await redis_client.setex(cache_key, ttl, "NULL")

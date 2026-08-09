"""Redis cache helpers for KPI caching and rate limiting."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from src.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the shared Redis connection pool."""
    global _pool  # noqa: PLW0603
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def cache_get(key: str) -> Any | None:
    """Retrieve a cached JSON value by key."""
    r = await get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    """Store a JSON-serializable value with a TTL."""
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def cache_invalidate(pattern: str) -> int:
    """Delete all keys matching a glob pattern. Returns count deleted."""
    r = await get_redis()
    keys = []
    async for key in r.scan_iter(match=pattern):
        keys.append(key)
    if keys:
        return await r.delete(*keys)
    return 0


async def rate_limit_check(key: str, max_calls: int, window_seconds: int) -> bool:
    """Simple sliding-window rate limiter. Returns True if allowed."""
    r = await get_redis()
    current = await r.get(key)
    if current is not None and int(current) >= max_calls:
        return False
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    await pipe.execute()
    return True


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        await _pool.aclose()
        _pool = None

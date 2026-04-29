from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger("fair-hiring.interview.redis")


class CacheBackend:
    async def get(self, key: str) -> str | None:
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError


class MemoryRedis(CacheBackend):
    """In-process async dict when REDIS_URL is unset."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            import time

            row = self._data.get(key)
            if not row:
                return None
            val, exp = row
            if exp is not None and time.monotonic() > exp:
                del self._data[key]
                return None
            return val

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        async with self._lock:
            import time

            exp = time.monotonic() + ttl_seconds if ttl_seconds else None
            self._data[key] = (value, exp)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)


class RedisClient(CacheBackend):
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds:
            await self._redis.setex(key, ttl_seconds, value)
        else:
            await self._redis.set(key, value)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def aclose(self) -> None:
        await self._redis.aclose()


_cache: CacheBackend | None = None
_real_redis: RedisClient | None = None


def get_cache() -> CacheBackend:
    global _cache, _real_redis
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        if _cache is None:
            _cache = MemoryRedis()
        return _cache
    if _real_redis is None:
        _real_redis = RedisClient(url)
        _cache = _real_redis
    return _cache


async def cache_set_json(key: str, obj: Any, ttl: int | None = 3600) -> None:
    await get_cache().set(key, json.dumps(obj), ttl)


async def cache_get_json(key: str) -> Any | None:
    raw = await get_cache().get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def shutdown_cache() -> None:
    global _real_redis, _cache
    if _real_redis is not None:
        await _real_redis.aclose()
        _real_redis = None
        _cache = None

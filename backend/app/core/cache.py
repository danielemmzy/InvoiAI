from __future__ import annotations

import json
import logging
import asyncio
import secrets
from datetime import timedelta
from typing import Any
from typing import TypeVar

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """
    Redis cache abstraction.

    Responsibilities
    ----------------
    • Read cache
    • Write cache
    • Delete cache
    • TTL management

    Used by
    --------
    • OCR
    • AI
    • Workers
    • Dashboard
    • Exchange rates

    No business logic.
    """

    # =====================================================
    # Get
    # =====================================================

    async def get(
        self,
        key: str,
    ) -> Any | None:

        try:
            redis = await get_redis()
            value = await redis.get(key)
        except Exception:
            logger.warning("Cache read failed; continuing without cache", exc_info=True)
            return None

        if value is None:
            return None

        try:
            return json.loads(value)
        except Exception:
            return value

    # =====================================================
    # Set
    # =====================================================

    async def set(
        self,
        *,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> None:

        try:
            redis = await get_redis()
        except Exception:
            logger.warning("Cache write skipped because Redis is unavailable", exc_info=True)
            return

        if not isinstance(
            value,
            str,
        ):
            value = json.dumps(
                value,
                default=str,
            )

        if isinstance(
            ttl,
            timedelta,
        ):
            ttl = int(
                ttl.total_seconds(),
            )

        try:
            await redis.set(key, value, ex=ttl)
        except Exception:
            logger.warning("Cache write failed; continuing without cache", exc_info=True)

    # =====================================================
    # Exists
    # =====================================================

    async def exists(
        self,
        key: str,
    ) -> bool:

        redis = await get_redis()

        return bool(
            await redis.exists(key),
        )

    # =====================================================
    # Delete
    # =====================================================

    async def delete(
        self,
        *keys: str,
    ) -> int:

        redis = await get_redis()

        return await redis.delete(
            *keys,
        )

    # =====================================================
    # Expire
    # =====================================================

    async def expire(
        self,
        *,
        key: str,
        ttl: int | timedelta,
    ) -> bool:

        redis = await get_redis()

        if isinstance(
            ttl,
            timedelta,
        ):
            ttl = int(
                ttl.total_seconds(),
            )

        return await redis.expire(
            key,
            ttl,
        )

    # =====================================================
    # Remember
    # =====================================================

    async def remember(
        self,
        *,
        key: str,
        ttl: int | timedelta,
        loader,
    ) -> Any:
        """
        Cache-aside helper.

        Example
        -------
        result = await cache.remember(
            key="exchange-rates",
            ttl=3600,
            loader=fetch_rates,
        )
        """

        cached = await self.get(
            key,
        )

        if cached is not None:
            return cached

        # Best-effort single-flight protection. If Redis is unavailable,
        # the request simply falls back to the normal cache-aside path.
        lock_key = f"{key}:lock"
        token = secrets.token_urlsafe(16)
        lock_acquired = False
        redis = None
        try:
            redis = await get_redis()
            lock_acquired = bool(await redis.set(lock_key, token, nx=True, ex=5))
        except Exception:
            pass

        if not lock_acquired and redis is not None:
            for _ in range(10):
                await asyncio.sleep(0.05)
                cached = await self.get(key)
                if cached is not None:
                    return cached

        try:
            value = await loader()
            await self.set(key=key, value=value, ttl=ttl)
            return value
        finally:
            if lock_acquired and redis is not None:
                try:
                    # Delete only our lock token; avoid releasing another worker's lock.
                    current = await redis.get(lock_key)
                    if current == token:
                        await redis.delete(lock_key)
                except Exception:
                    logger.debug("Cache lock cleanup failed", exc_info=True)

    # =====================================================
    # Increment
    # =====================================================

    async def increment(
        self,
        *,
        key: str,
        amount: int = 1,
    ) -> int:

        redis = await get_redis()

        return await redis.incr(
            key,
            amount,
        )


    async def delete_prefix(self, prefix: str) -> int:
        """Delete keys matching a prefix using SCAN (never KEYS)."""
        try:
            redis = await get_redis()
            keys = []
            async for key in redis.scan_iter(match=f"{prefix}*", count=200):
                keys.append(key)
            if not keys:
                return 0
            return int(await redis.delete(*keys))
        except Exception:
            logger.warning("Cache invalidation failed; database remains source of truth", exc_info=True)
            return 0
    # =====================================================
    # Flush
    # =====================================================

    async def clear(self) -> None:

        redis = await get_redis()

        await redis.flushdb()


cache = CacheService()

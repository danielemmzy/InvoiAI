from __future__ import annotations

from contextlib import asynccontextmanager

from redis.asyncio.lock import Lock

from app.core.cache_keys import lock
from app.core.redis import get_redis


class DistributedLock:
    """
    Redis distributed lock.

    Responsibilities
    ----------------
    • Prevent duplicate work
    • Synchronize workers
    • Protect critical sections

    Used by
    --------
    • Workers
    • OCR
    • AI
    • Sync Jobs
    • Scheduler

    No business logic.
    """

    async def acquire(
        self,
        *,
        name: str,
        timeout: int = 60,
        blocking: bool = True,
        blocking_timeout: int | None = None,
    ) -> Lock:

        redis = await get_redis()

        return redis.lock(
            name=lock(name),
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )

    @asynccontextmanager
    async def lock(
        self,
        *,
        name: str,
        timeout: int = 60,
        blocking: bool = True,
        blocking_timeout: int | None = None,
    ):

        redis_lock = await self.acquire(
            name=name,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )

        acquired = await redis_lock.acquire()

        if not acquired:
            raise RuntimeError(
                f"Unable to acquire distributed lock '{name}'."
            )

        try:
            yield

        finally:
            if await redis_lock.owned():
                await redis_lock.release()


distributed_lock = DistributedLock()
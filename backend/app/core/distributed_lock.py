from __future__ import annotations

import uuid
from typing import Any

from app.core.config import settings
from app.core.redis import get_redis


_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


_REFRESH_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('pexpire', KEYS[1], ARGV[2])
end
return 0
"""


class DistributedLock:
    """Redis-backed distributed lock for singleton work across processes."""

    def __init__(self, *, key: str, ttl_seconds: int | None = None) -> None:
        self.key = key
        self.ttl_seconds = ttl_seconds or settings.scheduler_lock_ttl_seconds
        self.token = uuid.uuid4().hex
        self._redis: Any | None = None
        self.acquired = False

    async def acquire(self) -> bool:
        if not settings.scheduler_lock_enabled:
            self.acquired = True
            return True

        try:
            self._redis = await get_redis()
            self.acquired = bool(
                await self._redis.set(
                    self.key,
                    self.token,
                    nx=True,
                    ex=self.ttl_seconds,
                )
            )
            return self.acquired
        except Exception:
            if settings.scheduler_lock_fail_open and settings.environment != "production":
                self.acquired = True
                return True
            return False

    async def refresh(self) -> bool:
        if not self.acquired or self._redis is None:
            return False
        try:
            return bool(await self._redis.eval(
                _REFRESH_SCRIPT,
                1,
                self.key,
                self.token,
                self.ttl_seconds * 1000,
            ))
        except Exception:
            return False

    async def release(self) -> None:
        if not self.acquired or self._redis is None:
            return
        try:
            await self._redis.eval(
                _RELEASE_SCRIPT,
                1,
                self.key,
                self.token,
            )
        finally:
            self.acquired = False

    async def __aenter__(self) -> bool:
        return await self.acquire()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.release()

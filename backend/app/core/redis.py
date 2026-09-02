"""
============================================================
app/core/redis.py

Redis Connection Manager

Redis is used for:

- Background job queues
- Rate limiting
- Distributed locks
- API caching
- Pub/Sub
- Temporary AI workflow state

Redis NEVER stores permanent business data.
PostgreSQL (Supabase) is always the source of truth.

Singleton async connection.
============================================================
"""

from __future__ import annotations

import logging

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


# ============================================================
# Connection
# ============================================================


async def get_redis() -> Redis:
    """
    Returns a singleton async Redis client.

    Usage
    -----
        redis = await get_redis()

        await redis.set("key", "value")

        value = await redis.get("key")
    """

    global _redis

    if _redis is None:

        _redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            max_connections=settings.redis_max_connections,
        )

        await _redis.ping()

        logger.info(
            "Redis initialized successfully."
        )

    return _redis


# ============================================================
# Health
# ============================================================


async def redis_health() -> bool:
    """
    Checks whether Redis is reachable.
    """

    try:

        redis = await get_redis()

        return await redis.ping()

    except Exception:

        logger.exception(
            "Redis health check failed."
        )

        return False


# ============================================================
# Shutdown
# ============================================================


async def close_redis() -> None:
    """
    Gracefully closes the Redis connection.
    """

    global _redis

    if _redis is not None:

        await _redis.aclose()

        _redis = None

        logger.info(
            "Redis connection closed."
        )
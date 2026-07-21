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

Singleton connection.
============================================================
"""

from __future__ import annotations

import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """
    Returns a singleton Redis client.

    Usage:
        redis = get_redis()
        redis.set("key", "value")
    """

    global _redis

    if _redis is None:
        _redis = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            health_check_interval=30,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

        _redis.ping()

        logger.info("Redis initialized")

    return _redis


def close_redis() -> None:
    """
    Gracefully closes Redis connection.
    """

    global _redis

    if _redis:
        _redis.close()
        _redis = None
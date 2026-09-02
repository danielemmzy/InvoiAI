from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from app.core.redis import get_redis


class PubSubService:
    """
    Redis Pub/Sub abstraction.

    Responsibilities
    ----------------
    • Publish events
    • Subscribe to channels
    • Stream messages

    Used by
    --------
    • Notifications
    • WebSockets
    • Workers
    • Scheduler

    No business logic.
    """

    # =====================================================
    # Publish
    # =====================================================

    async def publish(
        self,
        *,
        channel: str,
        message: Any,
    ) -> int:

        redis = await get_redis()

        payload = json.dumps(
            message,
            default=str,
        )

        return await redis.publish(
            channel,
            payload,
        )

    # =====================================================
    # Subscribe
    # =====================================================

    async def subscribe(
        self,
        *channels: str,
    ):

        redis = await get_redis()

        pubsub = redis.pubsub()

        await pubsub.subscribe(
            *channels,
        )

        return pubsub

    # =====================================================
    # Listen
    # =====================================================

    async def listen(
        self,
        pubsub,
    ) -> AsyncIterator[dict]:

        async for message in pubsub.listen():

            if (
                message["type"]
                != "message"
            ):
                continue

            data = message["data"]

            try:
                data = json.loads(data)

            except Exception:
                pass

            yield {
                "channel": message["channel"],
                "data": data,
            }

    # =====================================================
    # Unsubscribe
    # =====================================================

    async def unsubscribe(
        self,
        pubsub,
        *channels: str,
    ) -> None:

        await pubsub.unsubscribe(
            *channels,
        )

        await pubsub.aclose()


pubsub = PubSubService()
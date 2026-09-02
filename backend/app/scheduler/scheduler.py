from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Background scheduler.

    Responsibilities
    ----------------
    • Register periodic jobs
    • Start scheduled loops
    • Stop gracefully

    No business logic.
    """

    def __init__(self) -> None:

        self._tasks: list[asyncio.Task] = []

        self._running = False

    # =====================================================
    # Register
    # =====================================================

    def every(
        self,
        *,
        seconds: int,
        worker: Callable[[], Awaitable[None]],
    ) -> None:

        async def runner() -> None:

            while self._running:

                try:

                    await worker()

                except Exception:

                    logger.exception(
                        "Scheduled worker failed."
                    )

                await asyncio.sleep(seconds)

        self._tasks.append(
            asyncio.create_task(runner())
        )

    # =====================================================
    # Start
    # =====================================================

    async def start(self) -> None:

        self._running = True

        logger.info(
            "Scheduler started."
        )

    # =====================================================
    # Stop
    # =====================================================

    async def stop(self) -> None:

        self._running = False

        for task in self._tasks:

            task.cancel()

        if self._tasks:

            await asyncio.gather(
                *self._tasks,
                return_exceptions=True,
            )

        self._tasks.clear()

        logger.info(
            "Scheduler stopped."
        )


scheduler = Scheduler()
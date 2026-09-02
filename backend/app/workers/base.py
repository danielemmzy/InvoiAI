from __future__ import annotations

import asyncio
import logging
from abc import ABC
from abc import abstractmethod
from typing import Any


logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Base background worker.

    Responsibilities
    ----------------
    • Execute async jobs
    • Retry failed jobs
    • Central logging
    • Shared lifecycle

    Provider-agnostic.
    """

    def __init__(
        self,
        *,
        retries: int = 3,
        retry_delay: int = 5,
    ) -> None:

        self.retries = retries
        self.retry_delay = retry_delay

    # =========================================================
    # Public
    # =========================================================

    async def execute(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Execute worker with retries.
        """

        last_exception = None

        for attempt in range(1, self.retries + 1):

            try:

                logger.info(
                    "%s started (attempt %s/%s)",
                    self.__class__.__name__,
                    attempt,
                    self.retries,
                )

                result = await self.run(
                    **kwargs,
                )

                logger.info(
                    "%s completed",
                    self.__class__.__name__,
                )

                return result

            except Exception as exc:

                last_exception = exc

                logger.exception(
                    "%s failed (attempt %s/%s)",
                    self.__class__.__name__,
                    attempt,
                    self.retries,
                )

                if attempt < self.retries:

                    await asyncio.sleep(
                        self.retry_delay,
                    )

        assert last_exception is not None
        raise last_exception

    # =========================================================
    # Worker implementation
    # =========================================================

    @abstractmethod
    async def run(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Worker implementation.
        """
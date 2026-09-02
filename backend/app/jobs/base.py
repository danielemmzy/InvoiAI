from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any


class BaseJob(ABC):
    """
    Base background job.

    Responsibilities
    ----------------
    • Defines a standard interface for every queued job
    • Carries metadata
    • Provides retry configuration

    No queue implementation.

    No Redis logic.

    No business logic.
    """

    queue: str = "default"

    max_retries: int = 3

    retry_delay: int = 30

    timeout: int = 300

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """
        Execute the job.
        """
        raise NotImplementedError

    async def before_run(
        self,
        **kwargs: Any,
    ) -> None:
        """
        Hook executed before run().
        """

    async def after_run(
        self,
        result: Any,
        **kwargs: Any,
    ) -> None:
        """
        Hook executed after run().
        """

    async def on_failure(
        self,
        exc: Exception,
        **kwargs: Any,
    ) -> None:
        """
        Hook executed when the job fails.
        """

    async def execute(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Wrapper around the job lifecycle.
        """

        await self.before_run(**kwargs)

        try:

            result = await self.run(**kwargs)

            await self.after_run(
                result,
                **kwargs,
            )

            return result

        except Exception as exc:

            await self.on_failure(
                exc,
                **kwargs,
            )

            raise
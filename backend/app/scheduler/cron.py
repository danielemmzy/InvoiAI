from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from croniter import croniter


@dataclass(slots=True)
class CronJob:
    """
    Registered cron job.
    """

    name: str

    expression: str

    worker: Callable[[], Awaitable[None]]

    next_run: datetime


class CronScheduler:
    """
    Cron scheduler.

    Responsibilities
    ----------------
    • Register cron jobs
    • Calculate next execution
    • Return due jobs

    No execution.

    No asyncio.

    Used by scheduler.py.
    """

    def __init__(self) -> None:

        self._jobs: list[CronJob] = []

    # =====================================================
    # Register
    # =====================================================

    def register(
        self,
        *,
        name: str,
        expression: str,
        worker: Callable[[], Awaitable[None]],
    ) -> None:

        now = datetime.now(
            UTC,
        )

        iterator = croniter(
            expression,
            now,
        )

        self._jobs.append(
            CronJob(
                name=name,
                expression=expression,
                worker=worker,
                next_run=iterator.get_next(
                    datetime,
                ),
            )
        )

    # =====================================================
    # Due Jobs
    # =====================================================

    def due(
        self,
    ) -> list[CronJob]:

        now = datetime.now(
            UTC,
        )

        jobs: list[CronJob] = []

        for job in self._jobs:

            if job.next_run <= now:

                jobs.append(job)

                iterator = croniter(
                    job.expression,
                    now,
                )

                job.next_run = iterator.get_next(
                    datetime,
                )

        return jobs

    # =====================================================
    # Jobs
    # =====================================================

    @property
    def jobs(
        self,
    ) -> list[CronJob]:

        return self._jobs
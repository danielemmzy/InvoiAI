from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from app.jobs.base import BaseJob


class BaseJobQueue(ABC):
    """
    Base Job Queue.

    Responsibilities
    ----------------
    • Enqueue jobs
    • Execute jobs
    • Remove jobs
    • Query job status

    This class contains NO
    Redis/Celery/RQ implementation.

    Those implementations inherit
    from this interface.
    """

    # =====================================================
    # Enqueue
    # =====================================================

    @abstractmethod
    async def enqueue(
        self,
        *,
        job: BaseJob,
        kwargs: dict[str, Any] | None = None,
        delay: int = 0,
    ) -> str:
        """
        Queue a background job.

        Returns
        -------
        Job ID.
        """

    # =====================================================
    # Execute Immediately
    # =====================================================

    @abstractmethod
    async def execute(
        self,
        *,
        job: BaseJob,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute immediately.

        Useful for testing.
        """

    # =====================================================
    # Cancel
    # =====================================================

    @abstractmethod
    async def cancel(
        self,
        job_id: str,
    ) -> bool:
        """
        Cancel queued job.
        """

    # =====================================================
    # Status
    # =====================================================

    @abstractmethod
    async def status(
        self,
        job_id: str,
    ) -> str:
        """
        Return job status.

        queued

        running

        completed

        failed

        cancelled
        """

    # =====================================================
    # Result
    # =====================================================

    @abstractmethod
    async def result(
        self,
        job_id: str,
    ) -> Any:
        """
        Return completed job result.
        """

    # =====================================================
    # Retry
    # =====================================================

    @abstractmethod
    async def retry(
        self,
        job_id: str,
    ) -> bool:
        """
        Retry failed job.
        """

    # =====================================================
    # Delete
    # =====================================================

    @abstractmethod
    async def delete(
        self,
        job_id: str,
    ) -> bool:
        """
        Delete job completely.
        """
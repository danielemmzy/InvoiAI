from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """
    Standard background job statuses.

    Shared by
    ---------
    • Queue
    • Workers
    • Scheduler
    • Monitoring
    • Job history

    No provider-specific logic.
    """

    PENDING = "pending"

    QUEUED = "queued"

    RUNNING = "running"

    RETRYING = "retrying"

    COMPLETED = "completed"

    FAILED = "failed"

    CANCELLED = "cancelled"

    TIMED_OUT = "timed_out"

    DEAD_LETTER = "dead_letter"

    SKIPPED = "skipped"

    @classmethod
    def terminal(cls) -> set["JobStatus"]:
        """
        Final states.

        Once a job reaches one of these,
        it should no longer be scheduled.
        """

        return {
            cls.COMPLETED,
            cls.FAILED,
            cls.CANCELLED,
            cls.TIMED_OUT,
            cls.DEAD_LETTER,
            cls.SKIPPED,
        }

    @classmethod
    def active(cls) -> set["JobStatus"]:
        """
        States representing active work.
        """

        return {
            cls.PENDING,
            cls.QUEUED,
            cls.RUNNING,
            cls.RETRYING,
        }

    @classmethod
    def successful(cls) -> set["JobStatus"]:
        """
        Successful completion states.
        """

        return {
            cls.COMPLETED,
        }

    @classmethod
    def unsuccessful(cls) -> set["JobStatus"]:
        """
        Failed completion states.
        """

        return {
            cls.FAILED,
            cls.CANCELLED,
            cls.TIMED_OUT,
            cls.DEAD_LETTER,
        }
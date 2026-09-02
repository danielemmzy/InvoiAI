from __future__ import annotations

from enum import IntEnum


class JobPriority(IntEnum):
    """
    Standard priority levels for background jobs.

    Lower numbers represent higher priority.

    Used by
    -------
    • Queue implementations
    • Workers
    • Scheduler
    • Retry system
    """

    CRITICAL = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30
    BACKGROUND = 40

    @classmethod
    def default(cls) -> "JobPriority":
        """
        Default priority.
        """

        return cls.NORMAL

    @classmethod
    def ordered(cls) -> list["JobPriority"]:
        """
        Priorities ordered from highest
        to lowest.
        """

        return [
            cls.CRITICAL,
            cls.HIGH,
            cls.NORMAL,
            cls.LOW,
            cls.BACKGROUND,
        ]
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class JobResult:
    """
    Standard background job result.

    Responsibilities
    ----------------
    • Store execution outcome
    • Store execution metadata
    • Standardize worker responses

    Used by
    -------
    • Workers
    • Queues
    • Scheduler
    • Monitoring
    """

    job_id: str

    job_name: str

    success: bool

    result: Any = None

    error: str | None = None

    started_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    finished_at: datetime | None = None

    attempts: int = 1

    # =====================================================
    # Finish
    # =====================================================

    def complete(
        self,
        *,
        result: Any = None,
    ) -> None:

        self.success = True

        self.result = result

        self.finished_at = datetime.now(UTC)

    # =====================================================
    # Failure
    # =====================================================

    def fail(
        self,
        *,
        error: Exception | str,
    ) -> None:

        self.success = False

        self.error = str(error)

        self.finished_at = datetime.now(UTC)

    # =====================================================
    # Duration
    # =====================================================

    @property
    def duration(self) -> float | None:

        if self.finished_at is None:

            return None

        return (
            self.finished_at - self.started_at
        ).total_seconds()

    # =====================================================
    # Serialization
    # =====================================================

    def as_dict(
        self,
    ) -> dict:

        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "attempts": self.attempts,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "duration": self.duration,
        }
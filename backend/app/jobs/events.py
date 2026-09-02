from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class JobEvent:
    """
    Background job event.

    Responsibilities
    ----------------
    • Track job lifecycle
    • Emit worker events
    • Feed monitoring/logging systems

    No queue implementation.
    No Redis dependency.
    """

    job_id: str

    job_name: str

    event: str

    timestamp: datetime = datetime.now(UTC)

    payload: dict[str, Any] | None = None

    # =====================================================
    # Serialization
    # =====================================================

    def as_dict(
        self,
    ) -> dict:

        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload or {},
        }


class JobEvents:
    """
    Standard lifecycle events.

    Workers, schedulers and queues
    should use these names instead
    of hardcoded strings.
    """

    CREATED = "created"

    QUEUED = "queued"

    STARTED = "started"

    RETRYING = "retrying"

    COMPLETED = "completed"

    FAILED = "failed"

    CANCELLED = "cancelled"

    TIMED_OUT = "timed_out"

    SKIPPED = "skipped"

    DEAD_LETTER = "dead_letter"

    @classmethod
    def all(
        cls,
    ) -> list[str]:

        return [
            cls.CREATED,
            cls.QUEUED,
            cls.STARTED,
            cls.RETRYING,
            cls.COMPLETED,
            cls.FAILED,
            cls.CANCELLED,
            cls.TIMED_OUT,
            cls.SKIPPED,
            cls.DEAD_LETTER,
        ]
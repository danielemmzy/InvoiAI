"""
============================================================
Job Context

Runtime background job context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel

from app.core.enum.database import JobStatus, JobType


class JobContext(BaseModel):
    """
    Current background job.
    """

    job_id: UUID

    org_id: UUID

    job_type: JobType

    status: JobStatus

    attempts: int = 0

    max_attempts: int = 3

    priority: int = 0

    triggered_by: UUID | None = None

    request_id: str | None = None
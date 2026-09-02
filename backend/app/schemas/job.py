from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import JobStatus, JobType

"""
============================================================
Job Schemas

API request/response models.
============================================================
"""


# ============================================================
# Job Response
# ============================================================

class JobResponse(BaseModel):
    """
    Background job returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    job_type: JobType

    status: JobStatus

    resource_type: str

    resource_id: UUID | None

    payload: dict[str, Any]

    result: dict[str, Any]

    error: str | None

    error_stack: str | None

    priority: int

    attempts: int

    max_attempts: int

    next_retry_at: datetime | None

    redis_job_id: str | None

    queued_at: datetime

    started_at: datetime | None

    completed_at: datetime | None

    duration_ms: int | None

    triggered_by: UUID | None

    triggered_by_job: UUID | None


# ============================================================
# Job List
# ============================================================

class JobListResponse(BaseModel):

    items: list[JobResponse] = Field(default_factory=list)

    total: int
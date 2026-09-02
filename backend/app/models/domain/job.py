"""
============================================================
Background Job Domain Model

Mirrors PostgreSQL table.

- background_jobs

Repositories return this model only.
============================================================
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import JobStatus, JobType
from app.models.domain.base import DomainModel


JsonDict = dict[str, Any]


class BackgroundJob(DomainModel):
    """
    Mirrors background_jobs table.
    """

    id: UUID

    org_id: UUID

    job_type: JobType

    status: JobStatus

    resource_type: str

    resource_id: UUID | None = None

    payload: JsonDict = Field(default_factory=dict)

    result: JsonDict = Field(default_factory=dict)

    error: str | None = None

    error_stack: str | None = None

    priority: int

    attempts: int

    max_attempts: int

    next_retry_at: datetime | None = None

    redis_job_id: str | None = None

    queued_at: datetime

    started_at: datetime | None = None

    completed_at: datetime | None = None

    duration_ms: int | None = None

    triggered_by: UUID | None = None

    triggered_by_job: UUID | None = None
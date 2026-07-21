# ============================================================
# app/models/job.py
# Background Job models
#
# Redis executes jobs.
# PostgreSQL stores permanent job history.
#
# Used by:
# - OCR Worker
# - AI Analysis Worker
# - Embedding Worker
# - Sync Worker
# ============================================================

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.app.core.enum.enums import JobStatus, JobType


# ============================================================
# Create Job
# ============================================================

class JobCreate(BaseModel):
    """
    Create a background job.

    Usually created automatically after
    uploading a document.
    """

    org_id: str

    job_type: JobType

    priority: int = Field(default=5, ge=1, le=10)

    payload: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Update Job
# ============================================================

class JobUpdate(BaseModel):

    status: Optional[JobStatus] = None

    progress: Optional[int] = Field(None, ge=0, le=100)

    attempts: Optional[int] = Field(None, ge=0)

    error: Optional[str] = None

    worker_name: Optional[str] = None

    started_at: Optional[datetime] = None

    finished_at: Optional[datetime] = None


# ============================================================
# Job
# ============================================================

class Job(BaseModel):

    id: str

    org_id: str

    document_id: Optional[str] = None

    job_type: JobType

    status: JobStatus

    priority: int

    progress: int

    attempts: int

    max_attempts: int

    payload: dict[str, Any]

    result: Optional[dict[str, Any]] = None

    error: Optional[str] = None

    queue_name: str

    worker_name: Optional[str] = None

    created_by: Optional[str] = None

    created_at: Optional[datetime]

    started_at: Optional[datetime]

    finished_at: Optional[datetime]

    updated_at: Optional[datetime]


# ============================================================
# Job Summary
# ============================================================

class JobSummary(BaseModel):

    id: str

    job_type: JobType

    status: JobStatus

    progress: int

    priority: int

    created_at: Optional[datetime]

    finished_at: Optional[datetime]


# ============================================================
# Job Page
# ============================================================

class JobPage(BaseModel):

    jobs: list[JobSummary]

    count: int

    offset: int

    limit: int


# ============================================================
# Worker Heartbeat
# ============================================================

class WorkerHeartbeat(BaseModel):
    """
    Used by workers to report health.
    """

    worker_name: str

    queue_name: str

    active_jobs: int

    processed_today: int

    failed_today: int

    last_seen: datetime


# ============================================================
# Queue Statistics
# ============================================================

class QueueStatistics(BaseModel):

    queue_name: str

    pending: int

    running: int

    completed: int

    failed: int

    retrying: int
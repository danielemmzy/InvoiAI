from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

"""
============================================================
Profile Schemas

API request/response models.
============================================================
"""


# ============================================================
# Update Profile
# ============================================================

class ProfileUpdate(BaseModel):

    full_name: str | None = None

    avatar_url: str | None = None

    job_title: str | None = None

    department: str | None = None

    phone: str | None = None

    timezone: str | None = None

    language: str | None = None

    notification_prefs: dict[str, Any] | None = None

    ui_preferences: dict[str, Any] | None = None

    onboarding_completed: bool | None = None

    onboarding_step: int | None = None


# ============================================================
# Response
# ============================================================

class ProfileResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    full_name: str | None

    avatar_url: str | None

    job_title: str | None

    department: str | None

    phone: str | None

    timezone: str | None

    language: str | None

    notification_prefs: dict[str, Any]

    ui_preferences: dict[str, Any]

    onboarding_completed: bool

    onboarding_step: int

    last_active_at: datetime | None

    created_at: datetime

    updated_at: datetime
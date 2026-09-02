"""
============================================================
Profile Repository

Responsible ONLY for profile persistence.

No business logic.
No authentication.
No AI.

============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.profile_mapper import ProfileMapper
from app.models.domain.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository):
    """
    Repository for profiles table.
    """

    table_name = "profiles"

    mapper = ProfileMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def get_profile(
        self,
        profile_id: UUID,
    ) -> Profile | None:

        return await self.get(profile_id)

    async def update_profile(
        self,
        profile_id: UUID,
        data: dict,
    ) -> Profile | None:

        data["updated_at"] = datetime.now(UTC)

        return await self.update(
            profile_id,
            data,
        )

    # =========================================================
    # Avatar
    # =========================================================

    async def update_avatar(
        self,
        profile_id: UUID,
        avatar_url: str,
    ) -> Profile | None:

        return await self.update_profile(
            profile_id,
            {
                "avatar_url": avatar_url,
            },
        )

    # =========================================================
    # Preferences
    # =========================================================

    async def update_preferences(
        self,
        profile_id: UUID,
        notification_prefs: dict | None = None,
        ui_preferences: dict | None = None,
    ) -> Profile | None:

        values = {}

        if notification_prefs is not None:
            values["notification_prefs"] = notification_prefs

        if ui_preferences is not None:
            values["ui_preferences"] = ui_preferences

        return await self.update_profile(
            profile_id,
            values,
        )

    # =========================================================
    # Onboarding
    # =========================================================

    async def update_onboarding(
        self,
        profile_id: UUID,
        completed: bool,
        step: int,
    ) -> Profile | None:

        return await self.update_profile(
            profile_id,
            {
                "onboarding_completed": completed,
                "onboarding_step": step,
            },
        )

    # =========================================================
    # Activity
    # =========================================================

    async def update_last_active(
        self,
        profile_id: UUID,
    ) -> Profile | None:

        return await self.update_profile(
            profile_id,
            {
                "last_active_at": datetime.now(UTC),
            },
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def profile_exists(
        self,
        profile_id: UUID,
    ) -> bool:

        return await self.exists(
            "id",
            profile_id,
        )
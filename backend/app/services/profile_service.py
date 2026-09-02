"""
============================================================
Profile Service

Business logic for user profiles.

Responsibilities
----------------
- Retrieve profile
- Update profile
- Update avatar
- Update preferences
- Onboarding
- Last active tracking

NO SQL.
NO Supabase.

Repository handles persistence.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.models.domain.profile import Profile
from app.repositories.organization.profile_repository import (
    ProfileRepository,
)
from app.schemas.profile import (
    ProfileUpdate,
)


class ProfileService:
    """
    Profile business logic.
    """

    def __init__(
        self,
        repository: ProfileRepository,
    ):
        self.repository = repository

    # =========================================================
    # Retrieve
    # =========================================================

    async def get_profile(
        self,
        profile_id: UUID,
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        return profile

    # =========================================================
    # Update
    # =========================================================

    async def update_profile(
        self,
        profile_id: UUID,
        update: ProfileUpdate,
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        data = update.model_dump(
            exclude_unset=True,
        )

        return await self.repository.update_profile(
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
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        return await self.repository.update_avatar(
            profile_id,
            avatar_url,
        )

    # =========================================================
    # Preferences
    # =========================================================

    async def update_preferences(
        self,
        profile_id: UUID,
        notification_prefs: dict | None = None,
        ui_preferences: dict | None = None,
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        return await self.repository.update_preferences(
            profile_id,
            notification_prefs,
            ui_preferences,
        )

        # =========================================================
    # Onboarding
    # =========================================================

    async def complete_onboarding(
        self,
        profile_id: UUID,
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        return await self.repository.update_onboarding(
            profile_id,
            completed=True,
            step=profile.onboarding_step,
        )

    async def update_onboarding_step(
        self,
        profile_id: UUID,
        step: int,
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        completed = profile.onboarding_completed

        return await self.repository.update_onboarding(
            profile_id,
            completed=completed,
            step=step,
        )

    # =========================================================
    # Activity
    # =========================================================

    async def update_last_active(
        self,
        profile_id: UUID,
    ) -> Profile:

        profile = await self.repository.get_profile(
            profile_id,
        )

        if profile is None:
            raise ValueError(
                "Profile not found."
            )

        return await self.repository.update_last_active(
            profile_id,
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def profile_exists(
        self,
        profile_id: UUID,
    ) -> bool:

        return await self.repository.profile_exists(
            profile_id,
        )
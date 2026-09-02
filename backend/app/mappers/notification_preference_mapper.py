from __future__ import annotations

from app.mappers.base import BaseMapper
from app.models.domain.notification_preference import (
    NotificationPreference,
)


class NotificationPreferenceMapper(BaseMapper):
    """
    Maps notification preference rows.
    """

    domain_model = NotificationPreference

    @classmethod
    def to_domain(
        cls,
        data: dict | None,
    ) -> NotificationPreference | None:

        if not data:
            return None

        return NotificationPreference(
            id=data.get("id"),
            user_id=data.get("user_id"),
            email_enabled=data.get(
                "email_enabled",
                True,
            ),
            in_app_enabled=data.get(
                "in_app_enabled",
                True,
            ),
            push_enabled=data.get(
                "push_enabled",
                False,
            ),
            sms_enabled=data.get(
                "sms_enabled",
                False,
            ),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @classmethod
    def to_insert(
        cls,
        preference: NotificationPreference | dict,
    ) -> dict:

        if isinstance(
            preference,
            NotificationPreference,
        ):
            preference = preference.model_dump(
                exclude_none=True,
            )

        return {
            "user_id": preference["user_id"],
            "email_enabled": preference.get(
                "email_enabled",
                True,
            ),
            "in_app_enabled": preference.get(
                "in_app_enabled",
                True,
            ),
            "push_enabled": preference.get(
                "push_enabled",
                False,
            ),
            "sms_enabled": preference.get(
                "sms_enabled",
                False,
            ),
        }

    @classmethod
    def to_update(
        cls,
        preference: NotificationPreference | dict,
    ) -> dict:

        if isinstance(
            preference,
            NotificationPreference,
        ):
            preference = preference.model_dump(
                exclude_none=True,
            )

        return {
            k: v
            for k, v in preference.items()
            if k
            not in {
                "id",
                "created_at",
            }
        }
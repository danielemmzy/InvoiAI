"""Persistence for six-digit email verification challenges.

The repository stores only an HMAC-SHA256 hash of the code. It is the only
layer that talks to `auth_email_verifications`; the service layer decides
expiry, attempts, cooldown, and delivery.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase
from app.core.db import execute

TABLE = "auth_email_verifications"


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


class EmailVerificationRepository:
    def __init__(self, db=None) -> None:
        self.db = db or get_supabase()

    def _table(self):
        return self.db.table(TABLE)

    async def create(self, row: dict[str, Any]) -> dict[str, Any]:
        response = await execute(self._table().insert(row))
        data = response.data or []
        return data[0] if isinstance(data, list) else data

    async def latest_for_email(
        self,
        email: str,
        *,
        purpose: str = "email_verification",
    ) -> dict[str, Any] | None:
        rows = (
            await execute(
                self._table()
                .select("*")
                .eq("email", email.strip().lower())
                .eq("purpose", purpose)
                .order("created_at", desc=True)
                .limit(1)
            )
        ).data or []
        return rows[0] if rows else None

    async def recent_for_email(
        self,
        email: str,
        *,
        purpose: str = "email_verification",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return (
            await execute(
                self._table()
                .select("created_at")
                .eq("email", email.strip().lower())
                .eq("purpose", purpose)
                .order("created_at", desc=True)
                .limit(limit)
            )
        ).data or []

    async def latest_for_user(
        self,
        user_id: UUID | str,
    ) -> dict[str, Any] | None:
        rows = (
            await execute(
                self._table()
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(1)
            )
        ).data or []
        return rows[0] if rows else None

    def latest_status_for_user_sync(
        self,
        user_id: UUID | str,
    ) -> str | None:
        """Synchronous read used by token validation.

        Returns ``None`` when the user predates the OTP system, which keeps
        existing Supabase-confirmed accounts verified without a backfill.
        """
        rows = (
            self._table()
            .select("status")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        return rows[0].get("status")

    async def invalidate_pending(
        self,
        *,
        user_id: UUID | str,
        email: str,
        purpose: str = "email_verification",
    ) -> None:
        await execute(
            self._table()
            .update({"status": "expired", "updated_at": datetime.now(UTC).isoformat()})
            .eq("user_id", str(user_id))
            .eq("email", email.strip().lower())
            .eq("purpose", purpose)
            .eq("status", "pending")
        )

    async def update(
        self,
        challenge_id: UUID | str,
        values: dict[str, Any],
    ) -> dict[str, Any] | None:
        values = {**values, "updated_at": datetime.now(UTC).isoformat()}
        rows = (
            await execute(
                self._table()
                .update(values)
                .eq("id", str(challenge_id))
            )
        ).data or []
        return rows[0] if rows else None

    async def mark_verified(self, challenge_id: UUID | str) -> None:
        now = datetime.now(UTC).isoformat()
        await self.update(
            challenge_id,
            {"status": "verified", "verified_at": now},
        )

    async def increment_attempts(
        self,
        challenge_id: UUID | str,
        attempts: int,
        *,
        locked: bool,
    ) -> None:
        await self.update(
            challenge_id,
            {
                "attempts": attempts,
                "status": "locked" if locked else "pending",
            },
        )

    async def expire(self, challenge_id: UUID | str) -> None:
        await self.update(challenge_id, {"status": "expired"})


def latest_verification_status(user_id: UUID | str) -> str | None:
    return EmailVerificationRepository().latest_status_for_user_sync(user_id)

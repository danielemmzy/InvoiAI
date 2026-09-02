from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.stripe_event_mapper import StripeEventMapper
from app.models.domain.stripe_event import StripeEvent
from app.repositories.base import BaseRepository


class StripeEventRepository(BaseRepository):
    """Persistence boundary for Stripe webhook idempotency."""

    table_name = "stripe_events"
    mapper = StripeEventMapper

    async def get_by_stripe_event_id(self, stripe_event_id: str) -> StripeEvent | None:
        response = (
            self.table()
            .select("*")
            .eq("stripe_event_id", stripe_event_id)
            .limit(1)
            .execute()
        )
        return self._one(response)

    async def create_event(
        self,
        *,
        stripe_event_id: str,
        event_type: str,
        payload: dict,
    ) -> StripeEvent | None:
        now = datetime.now(UTC)
        return await self.create(
            {
                "stripe_event_id": stripe_event_id,
                "event_type": event_type,
                "status": "processing",
                "payload": payload,
                "attempts": 1,
                "processing_started_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )

    async def mark_processing(self, event_id: UUID) -> bool:
        response = (
            self.table()
            .update(
                {
                    "status": "processing",
                    "attempts": self._next_attempt(event_id),
                    "processing_started_at": datetime.now(UTC).isoformat(),
                    "last_error": None,
                    "failed_at": None,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(event_id))
            .eq("status", "failed")
            .execute()
        )
        return bool(response.data)

    def _next_attempt(self, event_id: UUID) -> int:
        response = (
            self.table().select("attempts").eq("id", str(event_id)).limit(1).execute()
        )
        row = response.data[0] if response.data else {}
        return int(row.get("attempts") or 0) + 1

    async def mark_processed(self, event_id: UUID) -> bool:
        response = (
            self.table()
            .update(
                {
                    "status": "processed",
                    "processed_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(event_id))
            .eq("status", "processing")
            .execute()
        )
        return bool(response.data)

    async def mark_failed(self, event_id: UUID, error: str) -> bool:
        response = (
            self.table()
            .update(
                {
                    "status": "failed",
                    "last_error": error[:4000],
                    "failed_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(event_id))
            .eq("status", "processing")
            .execute()
        )
        return bool(response.data)

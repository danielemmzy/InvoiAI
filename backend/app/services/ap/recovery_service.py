"""Durable recovery for Accounts Payable work.

AP used to be launched only from a request handler with
``asyncio.create_task``. If the API process restarted, the database still said
"in progress" but no worker existed. This service is the safety net: a cron
sweep finds documents that have not moved for a full lease period and
re-dispatches the correct idempotent step.

The document row remains authoritative. Redis only stores retry/backoff state,
so a Redis outage degrades to "retry on the next sweep" rather than losing an
invoice.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.enum.ap import APExceptionType, InvoiceAPStatus
from app.core.redis import get_redis
from app.core.supabase import get_supabase
from app.models.domain.ap import InvoiceException
from app.repositories.ap.exception_repository import InvoiceExceptionRepository
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.workers.ap_coding_worker import APCodingWorker
from app.workers.ap_matching_worker import APMatchingWorker

logger = logging.getLogger(__name__)

RECOVERABLE_STATUSES = (
    InvoiceAPStatus.VALIDATING.value,
    InvoiceAPStatus.MATCHING.value,
    InvoiceAPStatus.CODING.value,
)

BACKOFF_BASE_SECONDS = 60
BACKOFF_MAX_SECONDS = 900

_STATE_PREFIX = "invoiai:ap:recovery:v1"
_STATE_TTL_SECONDS = 7 * 24 * 60 * 60
_SWEEP_LOCK = "invoiai:ap:recovery-sweep"


from app.core.db import execute

def recovery_step(status: str | None) -> str | None:
    """Return the worker that can advance this AP status, if any."""
    if status in {InvoiceAPStatus.VALIDATING.value, InvoiceAPStatus.MATCHING.value}:
        return "matching"
    if status == InvoiceAPStatus.CODING.value:
        return "coding"
    return None


def _as_utc(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def is_stale(
    status: str | None,
    updated_at: datetime | str | None,
    *,
    now: datetime,
    lease_seconds: int,
) -> bool:
    """True only for an in-progress AP row older than the lease."""
    if status not in RECOVERABLE_STATUSES:
        return False
    timestamp = _as_utc(updated_at)
    if timestamp is None:
        return False
    return timestamp <= now - timedelta(seconds=lease_seconds)


def backoff_seconds(attempt: int) -> int:
    """Exponential backoff capped at the maximum sweep interval."""
    attempt = max(int(attempt), 1)
    return min(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), BACKOFF_MAX_SECONDS)


def dead_letter_state(status: str | None) -> tuple[str, str]:
    """The exception state and processing step for an unrecoverable document.

    A failed coding step is a coding exception; everything else failed before
    coding completed, so it belongs in the matching exception queue.
    """
    if status == InvoiceAPStatus.CODING.value:
        return InvoiceAPStatus.CODING_EXCEPTION.value, "ap_coding_error"
    return InvoiceAPStatus.MATCH_EXCEPTION.value, "ap_recovery_failed"


class APRecoveryService:
    """Find and resume AP documents abandoned by a lost background task."""

    def __init__(self, db=None) -> None:
        self.db = db or get_supabase()
        self.state = InvoiceStateMachine(self.db)

    @staticmethod
    def _state_key(document_id: UUID) -> str:
        return f"{_STATE_PREFIX}:{document_id}"

    async def _read_state(self, key: str) -> dict:
        try:
            redis = await get_redis()
            raw = await redis.get(key)
            return json.loads(raw) if raw else {}
        except Exception:
            logger.warning("Could not read AP recovery state from Redis", exc_info=True)
            return {}

    async def _write_state(self, key: str, state: dict) -> None:
        try:
            redis = await get_redis()
            await redis.setex(key, _STATE_TTL_SECONDS, json.dumps(state))
        except Exception:
            logger.warning("Could not persist AP recovery state to Redis", exc_info=True)

    async def clear(self, document_id: UUID) -> None:
        """Forget retry/backoff state after a deliberate human retry."""
        try:
            redis = await get_redis()
            await redis.delete(self._state_key(document_id))
        except Exception:
            logger.warning("Could not clear AP recovery state for %s", document_id, exc_info=True)

    async def list_stale(
        self,
        *,
        lease_seconds: int,
        limit: int,
        now: datetime | None = None,
    ) -> list[dict]:
        stale_before = (now or datetime.now(UTC)) - timedelta(seconds=lease_seconds)
        return (
            await execute(
                self.db.table("documents")
                .select("id,org_id,ap_status,updated_at")
                .eq("ap_enabled", True)
                .eq("document_type", "invoice")
                .in_("ap_status", list(RECOVERABLE_STATUSES))
                .lt("updated_at", stale_before.isoformat())
                .order("updated_at")
                .limit(limit)
            )
        ).data or []

    async def recover_one(
        self,
        row: dict,
        *,
        max_attempts: int,
    ) -> str:
        document_id = UUID(str(row["id"]))
        org_id = UUID(str(row["org_id"]))
        status = str(row.get("ap_status") or "")
        step = recovery_step(status)
        if step is None:
            return "skipped"

        key = self._state_key(document_id)
        state = await self._read_state(key)
        if state.get("dead"):
            return "dead"

        now = datetime.now(UTC)
        next_attempt_at = state.get("next_attempt_at")
        if isinstance(next_attempt_at, (int, float)) and next_attempt_at > now.timestamp():
            return "deferred"

        before = row.get("updated_at")
        try:
            if step == "matching":
                await APMatchingWorker(self.db).execute(document_id=document_id)
                current = await self.state.get_status(document_id)
                if current == InvoiceAPStatus.CODING:
                    await APCodingWorker(self.db).execute(document_id=document_id)
            else:
                await APCodingWorker(self.db).execute(document_id=document_id)
        except Exception as exc:
            return await self._record_failure(
                document_id=document_id,
                org_id=org_id,
                status=status,
                key=key,
                state=state,
                exc=exc,
                max_attempts=max_attempts,
            )

        updated = (
            (await execute(self.db.table("documents")
            .select("ap_status,updated_at")
            .eq("id", str(document_id))
            .limit(1)))
            .data
            or []
        )
        moved = bool(
            updated
            and (
                str(updated[0].get("ap_status")) != status
                or updated[0].get("updated_at") != before
            )
        )
        if moved:
            await self.clear(document_id)
            logger.info("AP recovery advanced invoice %s from %s", document_id, status)
            return "recovered"

        # The worker was already running, or made no state change. Do not count
        # this as a failure; the next sweep will look again.
        return "no_change"

    async def _record_failure(
        self,
        *,
        document_id: UUID,
        org_id: UUID,
        status: str,
        key: str,
        state: dict,
        exc: Exception,
        max_attempts: int,
    ) -> str:
        attempts = int(state.get("attempts") or 0) + 1
        state["attempts"] = attempts
        state["last_error"] = str(exc)[:500]

        logger.error(
            "AP recovery failed for %s (attempt %s/%s)",
            document_id,
            attempts,
            max_attempts,
            exc_info=exc,
        )

        if attempts >= max_attempts:
            state["dead"] = True
            exception_status, processing_step = dead_letter_state(status)
            is_coding_failure = exception_status == InvoiceAPStatus.CODING_EXCEPTION.value
            message = (
                f"AP automation could not recover this invoice after {attempts} attempts. "
                "The failure is recorded below; correct the cause and retry the workflow."
            )
            (await execute(self.db.table("documents").update(
                {
                    "status": "needs_review",
                    "processing_step": processing_step,
                    "processing_message": message,
                    "processing_progress": 85 if is_coding_failure else 55,
                    "gl_coding_status": "needs_review" if is_coding_failure else None,
                    "match_status": None if is_coding_failure else "exception",
                    "error_message": str(exc)[:500],
                }
            ).eq("id", str(document_id)).eq("org_id", str(org_id))))

            try:
                await self.state.transition(
                    document_id,
                    org_id,
                    InvoiceAPStatus(exception_status),
                    triggered_by="system",
                    reason=f"AP recovery gave up after {attempts} attempts",
                )
            except ValueError:
                # Another actor moved the document at the same moment; the
                # failure metadata above is still the useful record.
                logger.warning(
                    "Could not move %s to %s after recovery failure",
                    document_id,
                    exception_status,
                    exc_info=True,
                )

            if is_coding_failure:
                # CODING_EXCEPTION is resolvable only when the queue shows the
                # blocker. Reuse the existing GL coding exception type so the
                # reviewer can assign accounts and retry.
                repository = InvoiceExceptionRepository()
                repository.db = self.db
                await repository.upsert_open(
                    InvoiceException(
                        id=uuid4(),
                        org_id=org_id,
                        document_id=document_id,
                        exception_type=APExceptionType.GL_CODING_REQUIRED,
                        severity="warning",
                        title="GL coding could not finish",
                        description=message,
                        details={"error": str(exc)[:500], "retryable": True, "attempts": attempts},
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )

            await self._write_state(key, state)
            return "dead_lettered"

        state["next_attempt_at"] = datetime.now(UTC).timestamp() + backoff_seconds(attempts)
        await self._write_state(key, state)
        return "failed"

    async def run(
        self,
        *,
        lease_seconds: int | None = None,
        max_attempts: int | None = None,
        limit: int | None = None,
    ) -> dict:
        lease_seconds = lease_seconds or settings.ap_recovery_lease_seconds
        max_attempts = max_attempts or settings.ap_recovery_max_attempts
        limit = limit or settings.ap_recovery_sweep_limit

        lock = None
        try:
            redis = await get_redis()
            lock = redis.lock(_SWEEP_LOCK, timeout=55, blocking=False)
            if not await lock.acquire():
                return {"skipped": True, "reason": "sweep already running"}
        except Exception:
            logger.warning("AP recovery sweep lock unavailable; continuing without it", exc_info=True)

        try:
            rows = await self.list_stale(lease_seconds=lease_seconds, limit=limit)
            outcomes = {"recovered": 0, "failed": 0, "dead_lettered": 0, "deferred": 0, "no_change": 0, "dead": 0, "skipped": 0}
            for row in rows:
                outcome = await self.recover_one(row, max_attempts=max_attempts)
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
            result = {"stale": len(rows), **outcomes}
            if rows:
                logger.info("AP recovery sweep: %s", result)
            return result
        finally:
            if lock is not None:
                try:
                    await lock.release()
                except Exception:
                    logger.warning("Could not release AP recovery sweep lock", exc_info=True)

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.ap import PaymentAuthorizationStatus, PaymentInstructionStatus
from app.core.config import settings
from app.core.supabase import get_supabase
from app.repositories.ap.payment_instruction_repository import PaymentInstructionRepository
from app.services.payment.payment_authorization_service import PaymentAuthorizationService
from app.services.payment.payment_instruction_service import PaymentInstructionService

logger = logging.getLogger(__name__)


from app.core.db import execute

class ScheduledPaymentWorker:
    """Release approved scheduled payments on/after their requested date.

    Authorization is re-evaluated at release time; a schedule never bypasses
    a vendor hold, bank verification, W-9 requirement, or open exception.
    """
    def __init__(self, db=None):
        self.db = db or get_supabase()
        self.repository = PaymentInstructionRepository()
        self.instructions = PaymentInstructionService(self.db, repository=self.repository)
        self.authorization = PaymentAuthorizationService(self.db)

    async def run(self, limit: int = 100) -> dict[str, int]:
        today = datetime.now(UTC).date().isoformat()
        rows = (await execute(self.db.table("payment_instructions").select("id,org_id,document_id,scheduled_date,status").eq(
            "status", PaymentInstructionStatus.SCHEDULED.value
        ).lte("scheduled_date", today).order("scheduled_date").limit(limit))).data or []
        processed = failed = blocked = 0
        for row in rows:
            org_id = UUID(row["org_id"])
            instruction_id = UUID(row["id"])
            try:
                if self.instructions.provider.name == "mock" and not settings.debug:
                    await self.instructions.transition(
                        org_id=org_id, instruction_id=instruction_id,
                        to_status=PaymentInstructionStatus.BLOCKED, actor_id=None,
                        reason="No production payment provider is configured; payment was not released.",
                    )
                    blocked += 1
                    continue
                auth = await self.authorization.evaluate(org_id=org_id, document_id=UUID(row["document_id"]))
                if auth.status != PaymentAuthorizationStatus.AUTHORIZED:
                    await self.instructions.transition(
                        org_id=org_id, instruction_id=instruction_id,
                        to_status=PaymentInstructionStatus.BLOCKED, actor_id=None,
                        reason="Scheduled payment blocked at release-time compliance check: " + "; ".join(auth.blocked_reasons),
                    )
                    blocked += 1
                    continue
                await self.instructions.transition(
                    org_id=org_id, instruction_id=instruction_id,
                    to_status=PaymentInstructionStatus.AUTHORIZED, actor_id=None,
                    reason="Scheduled date reached and compliance checks passed",
                )
                await self.instructions.execute(org_id=org_id, instruction_id=instruction_id, actor_id=None)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Scheduled payment release failed for instruction %s", row.get("id"))
        return {"processed": processed, "blocked": blocked, "failed": failed}
